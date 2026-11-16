from app.modules.m5_quarantine.service import execute
from app.modules.m5_quarantine.rules import filter_rows,classify

def test_sample_five_bad(sample):assert sample['quarantine']['count']==5

def test_sample_reason_sum(sample):assert sum(r['count'] for r in sample['quarantine']['reasons'])==5

def test_sample_raw_evidence(sample):assert all(r['line']>1 and r['raw']['event_id'] for r in sample['quarantine']['rows'])

def test_empty_quarantine():assert execute([])['reasons']==[]

def test_reason_filter():assert filter_rows([{'code':'X'},{'code':'Y'}],'Y')==[{'code':'Y'}]

def test_recoverable_missing():assert execute([{'code':'NULL_VALUE'},{'code':'OVER_REFUND'}])['recoverable']==1

def test_over_refund_severity():assert classify([{'code':'OVER_REFUND'}])[0]['severity']=='严重'
