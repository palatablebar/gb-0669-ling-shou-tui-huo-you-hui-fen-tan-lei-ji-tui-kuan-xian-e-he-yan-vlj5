"""渠道退货持久台账。

设计要点：
- 事件号为主键，整单核算包在单个 SQLite 事务内；同事件号重试回放原结果，绝不二次冲减。
- 每次提交基于全量已确认事件按实际退货时间(UTC+事件号)重算，同步到达顺序不影响资格。
- 每行记录规则版本；规则更新后旧行 stale=1，原结果失效，/recover 用新规则重算，确认退货不丢失。
"""
import json
import os
import sqlite3
from pathlib import Path
from app.config import VERSION, CHANNELS
from app.errors import DomainError
from app.reasons import issue
from app.money import amount
from app.modules.m2_contract.rules import convert
from app.modules.m3_model.service import execute as model_execute
from app.modules.m4_calculate.service import execute as calculate_execute

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ledger_sales(
  event_id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL,
  fingerprint TEXT NOT NULL,
  payload TEXT NOT NULL,
  rule_version TEXT NOT NULL,
  created TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ledger_returns(
  event_id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL,
  channel TEXT NOT NULL,
  fingerprint TEXT NOT NULL,
  payload TEXT NOT NULL,
  rule_version TEXT NOT NULL,
  status TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '',
  owner TEXT NOT NULL DEFAULT '',
  stale INTEGER NOT NULL DEFAULT 0,
  created TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

def connect():
    path = Path(os.getenv('DB_PATH', 'state.sqlite'))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript(_SCHEMA)
    return db

def fingerprint(payload):
    base = {k: payload.get(k) for k in ('event_id', 'order_id', 'kind', 'sku', 'quantity', 'unit_price', 'discount', 'shipping', 'currency', 'time')}
    return json.dumps(base, sort_keys=True, ensure_ascii=False, separators=(',', ':'))

def _to_row(payload, line):
    raw = dict(payload)
    raw.setdefault('note', '')
    return {'line': line, 'raw': raw}

def _load_events(db):
    sales = [json.loads(r['payload']) for r in db.execute('SELECT payload FROM ledger_sales ORDER BY event_id')]
    returns = []
    for r in db.execute('SELECT channel,payload FROM ledger_returns ORDER BY event_id'):
        payload = json.loads(r['payload'])
        payload['channel'] = r['channel']
        returns.append(payload)
    return sales, returns

def _recompute(db):
    """在当前事务内基于全量台账事件重算，返回 m3/m4 结果。"""
    sales_raw, returns_raw = _load_events(db)
    converted = []
    bad = []
    for seq, payload in enumerate(sales_raw + returns_raw, 1):
        try:
            converted.append(convert(_to_row(payload, seq)))
        except DomainError as exc:
            bad.append(issue(_to_row(payload, seq), exc.code, exc.detail))
    model = model_execute(converted)
    calc = calculate_execute(model)
    calc['convert_quarantine'] = bad
    return model, calc

def _outcome_by_event(calc):
    accepted = {r['event_id']: r for r in calc['rows']}
    rejected = {r['raw']['event_id']: r for r in calc['quarantine']}
    return accepted, rejected

def _upsert_return(db, payload, channel):
    event_id = payload['event_id']
    fp = fingerprint(payload)
    row = db.execute('SELECT fingerprint,channel,status,stale FROM ledger_returns WHERE event_id=?', (event_id,)).fetchone()
    if row is not None:
        if row['fingerprint'] != fp or row['channel'] != channel:
            raise DomainError('EVENT_CONFLICT', f'事件号 {event_id} 已存在且内容/渠道不一致', 409)
        return False  # 幂等重试：不重复冲减
    db.execute('INSERT INTO ledger_returns(event_id,order_id,channel,fingerprint,payload,rule_version,status,detail,owner,stale) VALUES(?,?,?,?,?,?,?,?,?,0)',
               (event_id, payload['order_id'], channel, fp, json.dumps(payload, ensure_ascii=False), VERSION, 'PENDING', '', ''))
    return True

def _persist_outcomes(db, calc):
    accepted, rejected = _outcome_by_event(calc)
    for r in db.execute('SELECT event_id FROM ledger_returns').fetchall():
        eid = r['event_id']
        if eid in accepted:
            hit = accepted[eid]
            db.execute('UPDATE ledger_returns SET status=?,detail=?,owner=?,stale=0,rule_version=? WHERE event_id=?',
                       ('ACCEPTED', f"退款 {hit['refund']} 元（含运费 {hit['shipping']}）", hit['channel_label'], VERSION, eid))
        elif eid in rejected:
            hit = rejected[eid]
            db.execute('UPDATE ledger_returns SET status=?,detail=?,owner=?,stale=0,rule_version=? WHERE event_id=?',
                       ('REJECTED', hit['detail'], hit.get('owner_label', ''), VERSION, eid))
        else:
            db.execute('UPDATE ledger_returns SET status=?,detail=?,stale=0,rule_version=? WHERE event_id=?',
                       ('REJECTED', '未参与核算（原单缺失或字段隔离）', '', VERSION, eid))

def submit_return(payload, channel):
    """渠道提交一笔退货；返回整单重算后的唯一退款结果。"""
    if channel not in CHANNELS:
        raise DomainError('CHANNEL', '渠道仅支持 store / online')
    required = ('event_id', 'order_id', 'sku', 'quantity', 'unit_price', 'discount', 'shipping', 'currency', 'time')
    missing = [k for k in required if payload.get(k) in (None, '')]
    if missing:
        raise DomainError('NULL_VALUE', '必填字段缺失：' + ','.join(missing))
    payload = dict(payload)
    payload['kind'] = 'return'
    payload.setdefault('note', '')
    # 先做一次字段校验，非法输入不落台账，失败不影响已确认退货
    convert(_to_row(payload, 0))
    with connect() as db:
        created = _upsert_return(db, payload, channel)
        model, calc = _recompute(db)
        _persist_outcomes(db, calc)
        result = _snapshot(db, model, calc, target=payload['event_id'], created=created)
    return result

def import_sales(rows):
    """导入/更新销售目录（m2 转换后的行），随后重算受影响订单的退货。"""
    inserted = 0
    with connect() as db:
        for row in rows:
            if row.get('kind') != 'sale':
                continue
            payload = {k: row['raw'][k] for k in row['raw']}
            fp = fingerprint(payload)
            existing = db.execute('SELECT fingerprint FROM ledger_sales WHERE event_id=?', (row['event_id'],)).fetchone()
            if existing is None:
                db.execute('INSERT INTO ledger_sales(event_id,order_id,fingerprint,payload,rule_version) VALUES(?,?,?,?,?)',
                           (row['event_id'], row['order_id'], fp, json.dumps(payload, ensure_ascii=False), VERSION))
                inserted += 1
            elif existing['fingerprint'] != fp:
                raise DomainError('EVENT_CONFLICT', f"销售事件 {row['event_id']} 内容不一致", 409)
        model, calc = _recompute(db)
        _persist_outcomes(db, calc)
        snapshot = _snapshot(db, model, calc)
    snapshot['sales_inserted'] = inserted
    return snapshot

def recover():
    """失败恢复 / 规则更新重算：确认事件全部保留，按当前规则重新核算并刷新失效标记。"""
    with connect() as db:
        stale_before = db.execute('SELECT COUNT(*) c FROM ledger_returns WHERE stale=1 OR rule_version<>?', (VERSION,)).fetchone()['c']
        model, calc = _recompute(db)
        _persist_outcomes(db, calc)
        snapshot = _snapshot(db, model, calc)
    snapshot['recomputed'] = stale_before
    return snapshot

def mark_stale():
    """规则版本升级后将既有结果标记失效（不删除任何已确认退货）。"""
    with connect() as db:
        cur = db.execute('UPDATE ledger_returns SET stale=1 WHERE rule_version<>?', (VERSION,))
        return cur.rowcount

def _snapshot(db, model=None, calc=None, target=None, created=None):
    if calc is None:
        model, calc = _recompute_inline(db)
    ledger = [dict(r) for r in db.execute('SELECT event_id,order_id,channel,status,detail,owner,rule_version,stale,created FROM ledger_returns ORDER BY order_id,event_id').fetchall()]
    accepted, rejected = _outcome_by_event(calc)
    for item in ledger:
        item['stale'] = bool(item['stale']) or item['rule_version'] != VERSION
        item['channel_label'] = {'store': '门店', 'online': '线上'}.get(item['channel'], item['channel'])
        if item['event_id'] in accepted:
            item['latest'] = accepted[item['event_id']]
        elif item['event_id'] in rejected:
            item['latest'] = rejected[item['event_id']]
    target_row = next((x for x in ledger if x['event_id'] == target), None)
    return {
        'rule_version': VERSION,
        'created': created,
        'target': target_row,
        'ledger': ledger,
        'returns': calc['rows'],
        'rejected': calc['quarantine'],
        'events': calc['events'],
        'accounts': calc['accounts'],
        'refund_total': calc['refund_total'],
        'accepted_count': calc['accepted'],
        'quarantine': calc['convert_quarantine'],
        'model_paid': amount(sum(o['paid'] for o in model['orders'].values())),
        'order_count': len(model['orders']),
    }

def _recompute_inline(db):
    model, calc = _recompute(db)
    return model, calc

def queue(channel=None):
    with connect() as db:
        snapshot = _snapshot(db)
    if channel:
        snapshot['ledger'] = [x for x in snapshot['ledger'] if x['channel'] == channel]
    return snapshot

def reset():
    with connect() as db:
        db.execute('DELETE FROM ledger_returns')
        db.execute('DELETE FROM ledger_sales')
