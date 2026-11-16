import pytest
from app import store
from app.errors import DomainError
from app.modules.m7_batches.rules import validate
from app.modules.m7_batches.service import evidence_csv
from app.manifest import digest

def test_sample_idempotency(sample):assert store.save(sample)['created'];assert not store.save(sample)['created'];assert len(store.history())==1

def test_sample_old_review_rejected(sample):
    # TRAP-26
    data=store.save(sample);rid=data['manifest']['run_id'];assert store.review(rid,1)['revision']==2
    with pytest.raises(DomainError) as exc:store.review(rid,1)
    assert exc.value.status==409

def test_sample_export_has_all_bad_rows(sample):
    text=evidence_csv(sample);assert len(text.splitlines())==6;assert 'OVER_REFUND' in text

def test_source_hash_sensitive():assert digest(b'a',{})!=digest(b'b',{})

def test_unknown_parameter_rejected():
    with pytest.raises(DomainError):validate({'rate':99},{})

def test_missing_batch_404():
    with pytest.raises(DomainError) as exc:store.read('unknown')
    assert exc.value.status==404

def test_unbalanced_review_rejected(sample):
    sample['reconcile']['balanced']=False;data=store.save(sample)
    with pytest.raises(DomainError) as exc:store.review(data['manifest']['run_id'],1)
    assert exc.value.code=='UNBALANCED'
