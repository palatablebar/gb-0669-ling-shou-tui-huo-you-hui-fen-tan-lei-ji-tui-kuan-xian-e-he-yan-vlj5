from .rules import refund_one
from app.reasons import issue
from app.money import amount

def execute(model):
    state={};good=[];bad=[]
    for row in sorted(model['returns'],key=lambda r:(r['utc'],r['event_id'])):
        result,code=refund_one(model['orders'],state,row)
        if code:bad.append(issue(row,code))
        else:good.append(result)
    accounts=[]
    for oid,order in model['orders'].items():
        entry=state.get(oid,{'indices':[],'refunded':0,'shipping_refunded':False})
        remaining=order['paid']-entry['refunded']
        accounts.append({'order_id':oid,'paid':amount(order['paid']),'refunded':amount(entry['refunded']),'remaining':amount(remaining),'returned_quantity':len(entry['indices']),'sold_quantity':len(order['units']),'shipping_refunded':entry['shipping_refunded']})
    return {'rows':good,'quarantine':bad,'state':state,'accounts':accounts,'refund_total':amount(sum(x['refund_cents'] for x in good)),'accepted':len(good)}
