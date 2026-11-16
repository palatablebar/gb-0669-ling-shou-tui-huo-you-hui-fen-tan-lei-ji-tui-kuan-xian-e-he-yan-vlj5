from decimal import Decimal
from app.money import amount

def verify(model,calculation):
    paid=sum(o['paid'] for o in model['orders'].values());refunded=sum(r['refund_cents'] for r in calculation['rows'])
    remaining=sum(int(Decimal(r['remaining'])*100) for r in calculation['accounts'])
    discounts=sum(o['discount'] for o in model['orders'].values());allocated=sum(u['discount'] for o in model['orders'].values() for u in o['units'])
    negatives=[r['order_id'] for r in calculation['accounts'] if Decimal(r['remaining'])<0]
    return {'paid':amount(paid),'refunded':amount(refunded),'remaining':amount(remaining),'delta':amount(paid-refunded-remaining),'discount':amount(discounts),'allocated':amount(allocated),'balanced':paid==refunded+remaining and discounts==allocated and not negatives}
