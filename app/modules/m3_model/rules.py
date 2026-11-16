import json
from collections import defaultdict
from app.reasons import issue
from app.money import amount

def deduplicate(rows):
    groups=defaultdict(list)
    for row in rows:groups[row['event_id']].append(row)
    good=[];bad=[]
    for key,group in sorted(groups.items()):
        variants={json.dumps(x['raw'],sort_keys=True,ensure_ascii=False) for x in group}
        if len(variants)>1:bad.extend(issue(x,'CONFLICT') for x in group)
        else:good.append(group[0]);bad.extend(issue(x,'DUPLICATE') for x in group[1:])
    return good,bad

def allocate_units(lines):
    units=[]
    for row in sorted(lines,key=lambda r:r['sku']):
        for ordinal in range(row['qty']):units.append({'sku':row['sku'],'ordinal':ordinal+1,'price':row['price_cents'],'line':row['line']})
    gross=sum(u['price'] for u in units);discount=lines[0]['discount_cents']
    if discount>gross:return None,'ORDER_PROMO'
    for unit in units:unit['discount']=discount*unit['price']//gross;unit['remainder']=discount*unit['price']%gross
    tail=discount-sum(u['discount'] for u in units)
    ranking=sorted(range(len(units)),key=lambda i:(-units[i]['remainder'],units[i]['sku'],units[i]['ordinal']))
    for i in ranking[:tail]:units[i]['discount']+=1
    for unit in units:unit['net']=unit['price']-unit['discount']
    return {'units':units,'gross':gross,'discount':discount,'shipping':lines[0]['shipping_cents'],'paid':gross-discount+lines[0]['shipping_cents'],'sold_at':max(r['utc'] for r in lines)},None
