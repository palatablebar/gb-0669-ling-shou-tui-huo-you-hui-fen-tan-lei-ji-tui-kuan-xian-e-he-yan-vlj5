from copy import deepcopy
from app.modules.m6_reconcile.rules import verify
from app.modules.m4_calculate.service import execute

def test_sample_balanced(sample):assert sample['reconcile']['balanced']

def test_sample_money_conservation(sample):assert sample['reconcile']['paid']=='635.88';assert sample['reconcile']['refunded']=='324.00';assert sample['reconcile']['remaining']=='311.88';assert sample['reconcile']['delta']=='0.00'

def test_sample_row_conservation(sample):assert sample['reconcile']['input']==53;assert sample['reconcile']['accepted']==48;assert sample['reconcile']['isolated']==5

def test_discount_conservation(orders):
    out=verify(orders,execute(orders));assert out['discount']==out['allocated']=='60.00'

def test_tampered_remaining_detected(orders):
    calculation=execute(orders);calculation['accounts'][0]['remaining']='0.00';assert not verify(orders,calculation)['balanced']

def test_negative_remaining_detected(orders):
    calculation=execute(orders);calculation['accounts'][0]['remaining']='-1.00';assert not verify(orders,calculation)['balanced']

def test_refund_order_permutation_stable(orders):
    reverse=deepcopy(orders);reverse['returns'].reverse();assert execute(orders)['rows']==execute(reverse)['rows']
