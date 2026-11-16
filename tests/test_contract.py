import pytest
from app.modules.m2_contract.rules import number,convert
from app.modules.m2_contract.service import execute
from app.errors import DomainError

def test_sample_money_normalized(sample):
    # TRAP-06
    assert sample['contract']['rows'][0]['price_cents']==1999

def test_sample_currency_isolated(sample):assert any(r['code']=='CURRENCY' for r in sample['contract']['quarantine'])

def test_sample_leading_order_preserved(sample):
    # TRAP-08
    assert sample['contract']['rows'][0]['order_id']=='000001'

def test_missing_price_not_zero():
    # TRAP-07
    with pytest.raises(DomainError) as exc:number('N/A','单价')
    assert exc.value.code=='NULL_VALUE'

def test_overprecision_rejected():
    with pytest.raises(DomainError):number('1.001','金额')

def test_decimal_cents_exact():
    # TRAP-10
    assert sum(number('0.01','金额') for _ in range(1000))==1000

def test_quantity_zero_rejected(normalized):
    row=normalized[0]|{'raw':normalized[0]['raw']|{'quantity':'0'}};assert execute([row])['quarantine'][0]['code']=='NUMBER'

def test_unknown_kind(normalized):
    row=normalized[0]|{'raw':normalized[0]['raw']|{'kind':'cancel'}};assert execute([row])['quarantine'][0]['code']=='KIND'


def test_extreme_money_rejected():
    with pytest.raises(DomainError):number('1e1000000','金额')
