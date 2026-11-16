from .rules import convert
from app.reasons import issue
from app.errors import DomainError

def execute(rows):
    good=[];bad=[]
    for row in rows:
        try:good.append(convert(row))
        except DomainError as exc:bad.append(issue(row,exc.code,exc.detail))
    return {'rows':good,'quarantine':bad,'accepted':len(good),'policy':[{'field':'优惠','value':'按单件价格最大余额分摊'},{'field':'退货','value':'按原单件实付顺序退款'},{'field':'运费','value':'整单退完时仅退一次'},{'field':'币种','value':'CNY'},{'field':'金额精度','value':'0.01元'}]}
