from app.money import amount
from app.reasons import REASONS
from app.config import CHANNEL_LABELS

def _order_state(state, oid):
    return state.setdefault(oid, {'indices': [], 'owners': [], 'refunded': 0, 'shipping_refunded': False, 'events': []})

def _owner_label(channels):
    labels = [CHANNEL_LABELS.get(c, c) for c in dict.fromkeys(channels)]
    return '、'.join(labels)

def refund_one(orders, state, row):
    """按实际退货时间(UTC,事件号)顺序核算一次退货。

    同一事件号重试直接回放既有结果，不重复冲减；尾件资格由业务时间更早的渠道取得，
    同步先到但业务时间更晚的渠道返回 ELIGIBILITY_LOST。
    """
    oid = row['order_id']; sku = row['sku']; qty = row['qty']
    channel = row.get('channel', 'store')
    returned = _order_state(state, oid)
    for prior in returned['events']:
        if prior['event_id'] == row['event_id']:
            return dict(prior), prior.get('replay_code')
    if oid not in orders: return None, 'ORDER_MISSING'
    order = orders[oid]
    if row['utc'] < order['sold_at']: return None, 'BEFORE_SALE'
    available = [(i, u) for i, u in enumerate(order['units']) if u['sku'] == sku]
    if not available: return None, 'SKU_MISSING'
    remaining = [(i, u) for i, u in available if i not in returned['indices']]
    if len(remaining) < qty:
        holders = sorted({returned['owners'][returned['indices'].index(i)] for i, _ in available if i in returned['indices']})
        # 尾件已被其它渠道占用：资格冲突；仅本渠道历史占用导致的超量仍记 OVER_REFUND
        if any(h != channel for h in holders):
            return None, 'ELIGIBILITY_LOST', _owner_label(holders)
        return None, 'OVER_REFUND'
    chosen = remaining[:qty]
    new_indices = returned['indices'] + [i for i, u in chosen]
    shipping = order['shipping'] if len(new_indices) == len(order['units']) and not returned['shipping_refunded'] else 0
    value = sum(u['net'] for i, u in chosen) + shipping
    if returned['refunded'] + value > order['paid']:
        return None, 'OVER_REFUND'
    cumulative_before = order['paid'] - returned['refunded']
    returned['indices'] = new_indices
    returned['owners'] = returned['owners'] + [channel] * len(chosen)
    returned['refunded'] += value
    returned['shipping_refunded'] = returned['shipping_refunded'] or shipping > 0
    units = [{'sku': u.get('sku', sku), 'ordinal': u.get('ordinal', i + 1), 'net_cents': u['net'], 'net': amount(u['net'])} for i, u in chosen]
    ordinal_text = ','.join(str(u['ordinal']) for u in units)
    result = {
        'event_id': row['event_id'], 'order_id': oid, 'sku': sku, 'quantity': qty,
        'refund': amount(value), 'shipping': amount(shipping), 'refund_cents': value,
        'shipping_cents': shipping, 'line': row['line'], 'status': '通过',
        'channel': channel, 'channel_label': CHANNEL_LABELS.get(channel, channel),
        'units': units, 'units_text': f"{sku}×{qty}（件序 {ordinal_text}）",
        'cumulative_before_cents': cumulative_before, 'cumulative_before': amount(cumulative_before),
        'cumulative_after_cents': order['paid'] - returned['refunded'],
        'cumulative_after': amount(order['paid'] - returned['refunded']),
        'this_refund_cents': value, 'this_refund': amount(value),
        'shipping_owner': CHANNEL_LABELS.get(channel, channel) if shipping else '',
        'utc': row['utc'],
    }
    returned['events'].append(result)
    return result, None

def reject_detail(code, row, orders, state, owner_label=''):
    """为被拒渠道生成可读原因，包含取得资格的渠道与占用证据。"""
    detail = REASONS.get(code, code)
    oid = row.get('order_id')
    if code == 'ELIGIBILITY_LOST':
        detail = f"尾件资格已由{owner_label}渠道按实际退货时间取得，本次 {row.get('sku','')}×{row.get('qty','')} 不再冲减"
    elif code == 'OVER_REFUND' and oid in orders and oid in state:
        taken = len(state[oid]['indices'])
        detail = f"剩余可退件数不足：订单 {oid} 已退 {taken} 件，本次申请 {row.get('qty')} 件"
    elif code == 'OVER_REFUND':
        detail = f"退货数量超过剩余数量，本次申请 {row.get('qty')} 件"
    return detail
