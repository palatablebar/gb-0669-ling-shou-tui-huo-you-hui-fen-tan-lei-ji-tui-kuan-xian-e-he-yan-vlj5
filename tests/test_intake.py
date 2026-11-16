import pytest
from app.config import ROOT,COLUMNS
from app.modules.m1_intake.rules import parse
from app.modules.m1_intake.service import source
from app.errors import DomainError

def test_sample_bom_header(sample):
    # TRAP-02
    assert sample['intake']['input']==53

def test_legacy_chinese_data():
    # TRAP-01
    data=parse((ROOT/'sample_data/legacy.csv').read_bytes());assert data['encoding']=='gb18030';assert data['rows'][0]['raw']['note']=='门店011'

def test_sample_raw_fullwidth(sample):assert sample['intake']['rows'][0]['raw']['unit_price']=='１９.９９'

def test_empty_three_states():
    assert parse(b'')['state']=='EMPTY_FILE';assert parse(b'\n')['state']=='BLANK_ONLY';assert parse(','.join(COLUMNS).encode())['state']=='HEADER_ONLY'

def test_bad_columns_quarantined():assert parse((','.join(COLUMNS)+'\nx').encode())['quarantine'][0]['code']=='COLUMN_COUNT'

def test_bad_header_rejected():
    with pytest.raises(DomainError):parse(b'order,amount\n1,2')

def test_path_not_a_sample():
    with pytest.raises(DomainError):source({'sample':'../config'})
