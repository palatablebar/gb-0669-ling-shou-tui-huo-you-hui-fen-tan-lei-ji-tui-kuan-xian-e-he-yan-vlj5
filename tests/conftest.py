import pytest
from app.pipeline import run
from app.config import ROOT
from app.modules.m1_intake.rules import parse
from app.modules.m2_contract.service import execute as contract
from app.modules.m3_model.service import execute as model

@pytest.fixture
def sample():return run({'sample':'dirty'})

@pytest.fixture
def normalized():return contract(parse((ROOT/'sample_data/clean.csv').read_bytes())['rows'])['rows']

@pytest.fixture
def orders(normalized):return model(normalized)

@pytest.fixture(autouse=True)
def database(tmp_path,monkeypatch):monkeypatch.setenv('DB_PATH',str(tmp_path/'refund.sqlite'))
