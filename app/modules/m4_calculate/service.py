from .rules import refund_one, reject_detail
from app.reasons import issue
from app.money import amount
from app.config import CHANNEL_LABELS

def _unpack(outcome):
    # refund_one 对资格冲突返回 (None, code, owner)，其余返回 (None, code)
    if len(outcome) == 3:
        return outcome[0], outcome[1], outcome[2]
    return outcome[0], outcome[1], ''

def execute(model):
    """按实际退货时间(UTC+事件号)顺序核算；同步到达顺序不影响资格归属。"""
    state = {}; good = []; bad = []
    ordered = sorted(enumerate(model['returns']), key=lambda kv: (kv[1]['utc'], kv[1]['event_id']))
    for business_seq, (arrival_seq, row) in enumerate(ordered, 1):
        outcome = refund_one(model['orders'], state, row)
        result, code, owner = _unpack(outcome)
        if code:
            detail = reject_detail(code, row, model['orders'], state, owner)
            entry = issue(row, code, detail)
            entry['channel'] = row.get('channel', 'store')
            entry['channel_label'] = row.get('channel_label') or CHANNEL_LABELS.get(entry['channel'], entry['channel'])
            entry['utc'] = row['utc']
            entry['owner_label'] = owner
            bad.append(entry)
        else:
            result = dict(result)
            result['arrival_seq'] = arrival_seq + 1
            result['business_seq'] = business_seq
            result['sync_note'] = '同步先到' if arrival_seq + 1 < business_seq else ('同步后到' if arrival_seq + 1 > business_seq else '顺序一致')
            good.append(result)
    # 事件视图保持业务时间顺序，页面按此展示各次退货的占用与累计
    events = sorted(good, key=lambda r: (r['utc'], r['event_id']))
    accounts = []
    for oid, order in model['orders'].items():
        entry = state.get(oid, {'indices': [], 'owners': [], 'refunded': 0, 'shipping_refunded': False, 'events': []})
        remaining = order['paid'] - entry['refunded']
        sku_used = {}
        for idx in entry['indices']:
            unit = order['units'][idx]
            slot = sku_used.setdefault(unit['sku'], {'returned': 0})
            slot['returned'] += 1
        sku_channels = {}
        for idx, ch in zip(entry['indices'], entry['owners']):
            sku_channels.setdefault(order['units'][idx]['sku'], set()).add(ch)
        sku_summary = []
        seen = set()
        for unit in order['units']:
            if unit['sku'] in seen:
                continue
            seen.add(unit['sku'])
            total = sum(1 for u in order['units'] if u['sku'] == unit['sku'])
            used = sku_used.get(unit['sku'], {'returned': 0})['returned']
            chans = '、'.join(CHANNEL_LABELS[c] for c in sorted(sku_channels.get(unit['sku'], set())))
            sku_summary.append({'sku': unit['sku'], 'sold': total, 'returned': used, 'remaining': total - used, 'channels': chans or '—'})
        accounts.append({'order_id': oid, 'paid': amount(order['paid']), 'refunded': amount(entry['refunded']), 'remaining': amount(remaining), 'returned_quantity': len(entry['indices']), 'sold_quantity': len(order['units']), 'shipping_refunded': entry['shipping_refunded'], 'skus': sku_summary})
    return {'rows': good, 'events': events, 'quarantine': bad, 'state': state, 'accounts': accounts, 'refund_total': amount(sum(x['refund_cents'] for x in good)), 'accepted': len(good)}
