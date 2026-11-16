from copy import deepcopy
from app.modules.m4_calculate.rules import refund_one
from app.modules.m4_calculate.service import execute

def test_sample_refund_total(sample):assert sample['calculate']['refund_total']=='324.00'

def test_sample_remaining_total(sample):assert sample['reconcile']['remaining']=='311.88'

def test_sample_return_count(sample):assert sample['calculate']['accepted']==24

def test_sample_over_refund_isolated(sample):assert any(r['code']=='OVER_REFUND' for r in sample['calculate']['quarantine'])

def test_full_return_shipping_once():
    orders={'o':{'units':[{'sku':'A','net':100}],'shipping':20,'paid':120,'sold_at':'2026-01'}};state={};row={'order_id':'o','sku':'A','qty':1,'utc':'2026-02','event_id':'r','line':1}
    first,code=refund_one(orders,state,row);assert code is None;assert first['refund']=='1.20';assert first['shipping']=='0.20';before=deepcopy(state)
    # 同事件号重试：幂等回放，不二次冲减
    replay,code=refund_one(orders,state,row);assert code is None;assert replay['refund_cents']==first['refund_cents'];assert state==before
    # 新事件号再退：无剩余单位，拒绝且状态不变
    assert refund_one(orders,state,row|{'event_id':'r2'})[1]=='OVER_REFUND';assert state==before

def test_retry_same_event_does_not_deduct_twice():
    # 同一退货重试：回放原结果，累计与占用不变
    orders={'o':{'units':[{'sku':'A','net':100},{'sku':'A','net':100}],'shipping':0,'paid':200,'sold_at':'2026-01'}};state={};row={'order_id':'o','sku':'A','qty':1,'utc':'2026-02','event_id':'r','line':1}
    first,code=refund_one(orders,state,row);assert code is None;before=deepcopy(state)
    replay,code=refund_one(orders,state,row);assert code is None;assert replay['refund_cents']==first['refund_cents'];assert state==before
    next_row=row|{'event_id':'r2'};second,code=refund_one(orders,state,next_row);assert code is None;assert second['refund_cents']==100;assert state['o']['indices']==[0,1]

def test_unit_slices_do_not_overlap():
    # TRAP-23
    orders={'o':{'units':[{'sku':'A','net':66},{'sku':'A','net':67},{'sku':'A','net':67}],'shipping':0,'paid':200,'sold_at':'2026-01'}};state={}
    amounts=[refund_one(orders,state,{'order_id':'o','sku':'A','qty':1,'utc':'2026-02','event_id':f'r{i}','line':1})[0]['refund_cents'] for i in range(3)];assert amounts==[66,67,67];assert state['o']['indices']==[0,1,2]

def test_return_before_sale_rejected(orders):
    row=orders['returns'][0]|{'utc':'2025-01-01T00:00:00+00:00'};assert refund_one(orders['orders'],{},row)[1]=='BEFORE_SALE'

def test_unknown_sku_rejected(orders):
    row=orders['returns'][0]|{'sku':'missing'};assert refund_one(orders['orders'],{},row)[1]=='SKU_MISSING'
