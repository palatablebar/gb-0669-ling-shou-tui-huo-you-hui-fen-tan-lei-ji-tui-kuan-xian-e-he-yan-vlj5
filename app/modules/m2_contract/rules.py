import unicodedata
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from app.errors import DomainError
from app.config import NULLS, CHANNELS, CHANNEL_LABELS

def number(value,key,whole=False):
    text=unicodedata.normalize('NFKC',value).strip().replace(',','')
    if text in NULLS:raise DomainError('NULL_VALUE',key+'缺失')
    try:n=Decimal(text)
    except InvalidOperation:raise DomainError('NUMBER',key+'格式错误')
    if not n.is_finite() or n>Decimal('1000000000000') or n<0 or n!=(n.to_integral_value() if whole else n.quantize(Decimal('.01'))):raise DomainError('NUMBER',key+'精度或范围错误')
    return int(n) if whole else int(n*100)

def derive_channel(raw):
    explicit=raw.get('channel','').strip().lower()
    if explicit:
        if explicit not in CHANNELS:raise DomainError('KIND','渠道仅支持 store / online')
        return explicit
    note=raw.get('note','')
    if '线上' in note or 'online' in note.lower():return 'online'
    return 'store'

def convert(row):
    raw=row['raw'];r={k:('' if v is None else str(v).strip()) for k,v in raw.items()}
    if any(r[k] in NULLS for k in ('event_id','order_id','kind','sku')):raise DomainError('NULL_VALUE','业务标识不能为空')
    if r['kind'] not in ('sale','return'):raise DomainError('KIND','事件类型无效')
    if r['currency'].upper()!='CNY':raise DomainError('CURRENCY','币种不一致')
    try:
        time=datetime.fromisoformat(r['time'].replace('Z','+00:00'))
        if time.tzinfo is None:raise ValueError()
    except ValueError:raise DomainError('TIME','时间须带偏移')
    qty=number(r['quantity'],'件数',True)
    if qty<1 or qty>10000:raise DomainError('NUMBER','件数范围1至10000')
    channel=derive_channel(raw)
    out=r|{'line':row['line'],'raw':raw,'qty':qty,'channel':channel,'channel_label':CHANNEL_LABELS[channel],'utc':time.astimezone(timezone.utc).isoformat(),'price_cents':number(r['unit_price'],'单价'),'discount_cents':number(r['discount'],'优惠'),'shipping_cents':number(r['shipping'],'运费'),'currency':'CNY'}
    if r['kind']=='sale' and out['price_cents']==0:raise DomainError('NUMBER','销售单价须大于0')
    return out
