from fastapi.testclient import TestClient
from app.main import app

def test_every_module_page_and_export():
    client=TestClient(app);response=client.post('/api/batches',json={'sample':'dirty'});assert response.status_code==200;data=response.json();assert data['reconcile']['balanced'];rid=data['manifest']['run_id']
    for page in ('intake','contract','model','calculate','quarantine','reconcile','batches'):assert client.get('/'+page+'?run='+rid).status_code==200
    assert client.get('/api/export/'+rid).status_code==200

def test_invalid_header_returns422():assert TestClient(app).post('/api/intake',json={'csv':'order,price\n1,2'}).status_code==422

def test_clean_dirty_same_business_result():
    client=TestClient(app);a=client.post('/api/batches',json={'sample':'clean'}).json();b=client.post('/api/batches',json={'sample':'dirty'}).json();assert a['quarantine']['count']==0;assert b['quarantine']['count']==5;assert a['reconcile']['refunded']==b['reconcile']['refunded']
