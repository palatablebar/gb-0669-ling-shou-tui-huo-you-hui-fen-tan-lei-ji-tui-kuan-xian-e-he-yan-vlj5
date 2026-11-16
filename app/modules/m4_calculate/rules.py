from app.money import amount

def refund_one(orders,state,row):
    oid=row['order_id'];sku=row['sku'];qty=row['qty']
    if oid not in orders:return None,'ORDER_MISSING'
    order=orders[oid]
    if row['utc']<order['sold_at']:return None,'BEFORE_SALE'
    available=[(i,u) for i,u in enumerate(order['units']) if u['sku']==sku]
    if not available:return None,'SKU_MISSING'
    returned=state.setdefault(oid,{'indices':[],'refunded':0,'shipping_refunded':False})
    remaining=[(i,u) for i,u in available if i not in returned['indices']]
    if len(remaining)<qty:return None,'OVER_REFUND'
    chosen=remaining[:qty];new_indices=returned['indices']+[i for i,u in chosen]
    shipping=order['shipping'] if len(new_indices)==len(order['units']) and not returned['shipping_refunded'] else 0
    value=sum(u['net'] for i,u in chosen)+shipping
    if returned['refunded']+value>order['paid']:return None,'OVER_REFUND'
    returned['indices']=new_indices;returned['refunded']+=value;returned['shipping_refunded']=returned['shipping_refunded'] or shipping>0
    return {'event_id':row['event_id'],'order_id':oid,'sku':sku,'quantity':qty,'refund':amount(value),'shipping':amount(shipping),'refund_cents':value,'shipping_cents':shipping,'line':row['line'],'status':'通过'},None
