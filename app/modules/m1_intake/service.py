import base64
from app.config import ROOT
from app.errors import DomainError
from .rules import parse

def source(payload):
    sample=payload.get('sample','dirty')
    if 'csv' in payload:
        if not isinstance(payload['csv'],str):raise DomainError('CSV_TYPE','CSV必须为文本')
        return payload['csv'].encode('utf-8')
    if 'base64' in payload:
        try:return base64.b64decode(payload['base64'],validate=True)
        except (ValueError,TypeError):raise DomainError('BASE64','文件内容无效')
    if sample not in ('dirty','clean'):raise DomainError('SAMPLE','样例名称无效')
    return (ROOT/'sample_data'/f'{sample}.csv').read_bytes()

def execute(payload):
    raw=source(payload)
    return raw,parse(raw)
