from app import ledger
from app.errors import DomainError
from app.reasons import issue
from app.modules.m2_contract.rules import convert
from .rules import validate_submission, validate_import

def submit(payload):
    channel, event = validate_submission(payload)
    return ledger.submit_return(event, channel)

def import_catalog(payload):
    rows = validate_import(payload)
    converted = []
    bad = []
    for seq, raw in enumerate(rows, 1):
        try:
            converted.append(convert({'line': seq, 'raw': raw}))
        except DomainError as exc:
            bad.append(issue({'line': seq, 'raw': raw}, exc.code, exc.detail))
    snapshot = ledger.import_sales(converted)
    snapshot['import_quarantine'] = bad
    return snapshot

def recover():
    return ledger.recover()

def queue(channel=None):
    if channel and channel not in ('store', 'online'):
        raise DomainError('CHANNEL', '渠道仅支持 store / online')
    return ledger.queue(channel)
