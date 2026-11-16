from fastapi.testclient import TestClient
from app.main import app

def test_every_module_page_and_export():
    client=TestClient(app);response=client.post('/api/batches',json={'sample':'dirty'});assert response.status_code==200;data=response.json();assert data['reconcile']['balanced'];rid=data['manifest']['run_id']
    for page in ('intake','contract','model','calculate','channels','quarantine','reconcile','batches'):assert client.get('/'+page+'?run='+rid).status_code==200
    assert client.get('/api/export/'+rid).status_code==200

def test_invalid_header_returns422():assert TestClient(app).post('/api/intake',json={'csv':'order,price\n1,2'}).status_code==422

def test_clean_dirty_same_business_result():
    client=TestClient(app);a=client.post('/api/batches',json={'sample':'clean'}).json();b=client.post('/api/batches',json={'sample':'dirty'}).json();assert a['quarantine']['count']==0;assert b['quarantine']['count']==5;assert a['reconcile']['refunded']==b['reconcile']['refunded']

def test_contest_sample_eligibility_and_rejection_reasons():
    client=TestClient(app);data=client.post('/api/batches',json={'sample':'contest'}).json()
    assert data['reconcile']['balanced']
    calc=data['calculate']
    # 门店实际退货更早，线上同步先到仍被拒
    rejected={q['raw']['event_id']:q for q in calc['quarantine']}
    assert rejected['R101']['code']=='ELIGIBILITY_LOST'
    assert rejected['R101']['channel_label']=='线上' and rejected['R101']['owner_label']=='门店'
    # 同刻退货按事件号决胜
    assert rejected['R202']['owner_label']=='线上'
    # 每次退货都带占用、累计可退与资格归属
    for row in calc['events']:
        assert row['units'] and row['cumulative_before'] and row['this_refund'] and row['channel_label']
    # 整单退完运费仅一次且归属线上渠道
    r301=next(r for r in calc['events'] if r['event_id']=='R301')
    assert r301['shipping']=='6.00' and r301['shipping_owner']=='线上'
