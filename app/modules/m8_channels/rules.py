from app.errors import DomainError
from app.config import CHANNELS

def validate_submission(payload):
    if not isinstance(payload, dict):
        raise DomainError('PAYLOAD', '请求体必须为对象')
    channel = payload.get('channel', 'store')
    if channel not in CHANNELS:
        raise DomainError('CHANNEL', '渠道仅支持 store / online')
    event = payload.get('event')
    if not isinstance(event, dict):
        raise DomainError('PAYLOAD', 'event 必须为退货事件对象')
    return channel, dict(event)

def validate_import(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('rows'), list):
        raise DomainError('PAYLOAD', 'rows 必须为事件数组')
    return payload['rows']
