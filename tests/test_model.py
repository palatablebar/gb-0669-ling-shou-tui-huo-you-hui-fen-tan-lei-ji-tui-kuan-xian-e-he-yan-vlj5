from copy import deepcopy
from app.modules.m3_model.rules import allocate_units
from app.modules.m3_model.service import execute

def test_sample_order_count(sample):assert sample['model']['order_count']==12

def test_sample_paid_total(sample):assert sample['model']['paid']=='635.88'

def test_sample_line_discount(sample):assert sample['model']['rows'][0]['discount']=='4.00';assert sample['model']['rows'][1]['discount']=='1.00'

def test_largest_remainder_counterexample():
    # TRAP-24
    rows=[{'sku':'A','qty':3,'price_cents':100,'discount_cents':100,'shipping_cents':0,'utc':'2026','line':1}]
    order,code=allocate_units(rows);assert code is None;assert [u['discount'] for u in order['units']]==[34,33,33];assert sum(u['discount'] for u in order['units'])==100

def test_order_promotion_conflict(normalized):
    rows=deepcopy(normalized);rows[0]['discount_cents']=999;out=execute(rows);assert len([r for r in out['quarantine'] if r['code']=='ORDER_PROMO'])==2

def test_over_gross_discount_rejected():
    rows=[{'sku':'A','qty':1,'price_cents':100,'discount_cents':101,'shipping_cents':0,'utc':'2026','line':1}];assert allocate_units(rows)==(None,'ORDER_PROMO')

def test_reorder_stable(normalized):assert execute(normalized)['rows']==execute(list(reversed(normalized)))['rows']

def test_sample_duplicate_reason(sample):
    # TRAP-14
    assert any(r['code']=='DUPLICATE' for r in sample['model']['quarantine'])
