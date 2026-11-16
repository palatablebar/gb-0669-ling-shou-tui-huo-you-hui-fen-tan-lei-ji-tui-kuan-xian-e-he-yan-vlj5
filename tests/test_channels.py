"""渠道并发退货：资格归属、幂等重试、规则失效与失败恢复。"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import ledger
from app.errors import DomainError

SALE = {'event_id': 'S1', 'order_id': 'O1', 'kind': 'sale', 'sku': 'A', 'quantity': '1',
        'unit_price': '100.00', 'discount': '0', 'shipping': '10.00', 'currency': 'CNY',
        'time': '2026-11-01T08:00:00+08:00', 'note': '', 'channel': 'store'}

def event(eid, oid='O1', sku='A', qty=1, when='2026-11-03T08:00:00+08:00'):
    return {'event_id': eid, 'order_id': oid, 'sku': sku, 'quantity': qty, 'unit_price': '0',
            'discount': '0', 'shipping': '0', 'currency': 'CNY', 'time': when, 'note': ''}

@pytest.fixture(autouse=True)
def clean_ledger():
    ledger.reset()
    yield
    ledger.reset()

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def catalog(client):
    res = client.post('/api/channels/import', json={'rows': [SALE]})
    assert res.status_code == 200
    return res.json()

def test_actual_return_time_beats_sync_arrival(client, catalog):
    # 线上同步先到但实际退货晚；门店实际退货更早 -> 门店取得尾件资格
    late_online = event('R-LATE', when='2026-11-05T08:00:00+08:00')
    early_store = event('R-EARLY', when='2026-11-02T08:00:00+08:00')
    client.post('/api/channels/submit', json={'channel': 'online', 'event': late_online})
    snap = client.post('/api/channels/submit', json={'channel': 'store', 'event': early_store}).json()
    statuses = {x['event_id']: x['status'] for x in snap['ledger']}
    assert statuses['R-EARLY'] == 'ACCEPTED'
    assert statuses['R-LATE'] == 'REJECTED'
    rejected = next(x for x in snap['ledger'] if x['event_id'] == 'R-LATE')
    assert '门店' in rejected['detail'] and rejected['owner'] == '门店'
    # 唯一退款结果：只冲减一次
    assert snap['refund_total'] == '110.00'
    assert snap['accepted_count'] == 1

def test_same_utc_tiebreak_by_event_id(client, catalog):
    a = event('R-Z', when='2026-11-03T10:00:00+08:00')
    b = event('R-A', when='2026-11-03T10:00:00+08:00')
    client.post('/api/channels/submit', json={'channel': 'online', 'event': a})
    snap = client.post('/api/channels/submit', json={'channel': 'store', 'event': b}).json()
    statuses = {x['event_id']: x['status'] for x in snap['ledger']}
    assert statuses['R-A'] == 'ACCEPTED'
    assert statuses['R-Z'] == 'REJECTED'

def test_retry_same_event_is_idempotent(client, catalog):
    payload = {'channel': 'online', 'event': event('R1')}
    first = client.post('/api/channels/submit', json=payload).json()
    assert first['created'] is True
    second = client.post('/api/channels/submit', json=payload).json()
    assert second['created'] is False
    assert second['refund_total'] == '110.00'
    assert len(second['ledger']) == 1
    queue = client.get('/api/channels/queue').json()
    assert len(queue['ledger']) == 1
    assert queue['refund_total'] == '110.00'

def test_same_event_different_payload_conflicts(client, catalog):
    client.post('/api/channels/submit', json={'channel': 'online', 'event': event('R1')})
    res = client.post('/api/channels/submit', json={'channel': 'online', 'event': event('R1', qty=2)})
    assert res.status_code == 409
    assert res.json()['code'] == 'EVENT_CONFLICT'
    # 冲突不改变已确认退款
    assert client.get('/api/channels/queue').json()['refund_total'] == '110.00'

def test_invalid_event_never_persisted(client, catalog):
    bad = event('R-BAD', when='2026-11-03T08:00:00')  # 缺少时区偏移
    res = client.post('/api/channels/submit', json={'channel': 'store', 'event': bad})
    assert res.status_code == 422
    assert client.get('/api/channels/queue').json()['ledger'] == []

def test_recovery_preserves_confirmed_returns(client, catalog):
    client.post('/api/channels/submit', json={'channel': 'store', 'event': event('R1')})
    rec = client.post('/api/channels/recover').json()
    assert [(x['event_id'], x['status']) for x in rec['ledger']] == [('R1', 'ACCEPTED')]
    assert rec['refund_total'] == '110.00'

def test_rule_bump_invalidates_and_recompute(monkeypatch, client, catalog):
    client.post('/api/channels/submit', json={'channel': 'store', 'event': event('R1')})
    monkeypatch.setattr(ledger, 'VERSION', '2099.01.1')
    assert ledger.mark_stale() == 1
    queue = client.get('/api/channels/queue').json()
    assert queue['ledger'][0]['stale'] is True
    # 恢复：确认退货不丢，按新规则重算后失效标记清除
    rec = client.post('/api/channels/recover').json()
    assert rec['recomputed'] == 1
    assert rec['ledger'][0]['status'] == 'ACCEPTED'
    assert rec['ledger'][0]['stale'] is False
    assert rec['refund_total'] == '110.00'

def test_stale_run_review_blocked(monkeypatch, client, catalog):
    run = client.post('/api/batches', json={'sample': 'clean'}).json()
    rid = run['manifest']['run_id']
    monkeypatch.setattr('app.store.VERSION', '2099.01.1')
    stale = client.get('/api/run/' + rid).json()
    assert stale['stale'] is True
    res = client.post('/api/review/' + rid, json={'revision': stale['revision']})
    assert res.status_code == 409
    assert res.json()['code'] == 'RULE_STALE'

def test_full_return_shipping_owner_is_channel(client):
    sale = dict(SALE, shipping='10.00')
    client.post('/api/channels/import', json={'rows': [sale]})
    snap = client.post('/api/channels/submit', json={'channel': 'online', 'event': event('R1')}).json()
    row = snap['returns'][0]
    assert row['shipping'] == '10.00'
    assert row['shipping_owner'] == '线上'
    assert row['cumulative_before'] == '110.00'
    assert row['cumulative_after'] == '0.00'
