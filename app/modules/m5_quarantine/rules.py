from collections import Counter
from app.reasons import REASONS

def classify(rows):
    reasons=Counter(row['code'] for row in rows)
    return [{'code':code,'reason':REASONS.get(code,code),'count':count,'severity':'严重' if code in ('CONFLICT','BALANCE','OVERLAP','OVER_REFUND') else '警告'} for code,count in sorted(reasons.items())]

def filter_rows(rows,code=None):
    return [r for r in rows if not code or r['code']==code]
