import csv
import io
from app.config import COLUMNS, MAX_ROWS, MAX_BYTES
from app.errors import DomainError
from app.reasons import issue

def decode(raw):
    if len(raw)>MAX_BYTES: raise DomainError('TOO_LARGE','文件超过2MB',413)
    for encoding in ('utf-8-sig','gb18030'):
        try: return raw.decode(encoding),encoding
        except UnicodeDecodeError: pass
    raise DomainError('ENCODING','编码无法识别')

def parse(raw):
    text,encoding=decode(raw)
    if not text: return {'rows':[],'quarantine':[],'input':0,'blank':0,'headers':0,'encoding':encoding,'state':'EMPTY_FILE'}
    reader=csv.reader(io.StringIO(text,newline=''),strict=True)
    rows=[];bad=[];blank=0;headers=0;count=0
    try:
        header=next(reader,None)
        if header is None: header=[]
        if not header or all(not c.strip() for c in header):
            if not text.strip():return {'rows':[],'quarantine':[],'input':0,'blank':len(text.splitlines()),'headers':0,'encoding':encoding,'state':'BLANK_ONLY'}
        header=[c.strip().lstrip('\ufeff') for c in header]
        if len(set(header))!=len(header) or set(header)!=set(COLUMNS): raise DomainError('HEADER','字段不匹配')
        for values in reader:
            if not values or all(not v.strip() for v in values): blank+=1;continue
            if values==header: headers+=1;continue
            count+=1
            if count>MAX_ROWS:raise DomainError('TOO_MANY_ROWS','记录超过10000行',413)
            row={'line':reader.line_num,'raw':dict(zip(header,values))}
            if len(values)!=len(header):bad.append(issue(row,'COLUMN_COUNT','字段数量不一致'));continue
            rows.append(row)
    except csv.Error as exc: raise DomainError('CSV_BROKEN',f'CSV结构错误：{exc}')
    return {'rows':rows,'quarantine':bad,'input':count,'blank':blank,'headers':headers,'encoding':encoding,'state':'READY' if count else 'HEADER_ONLY'}
