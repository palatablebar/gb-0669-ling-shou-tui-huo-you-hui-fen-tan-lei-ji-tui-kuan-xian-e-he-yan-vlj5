import time
from app.modules.m1_intake.service import execute as intake
from app.modules.m2_contract.service import execute as contract
from app.modules.m3_model.service import execute as model
from app.modules.m4_calculate.service import execute as calculate
from app.modules.m5_quarantine.service import execute as quarantine
from app.modules.m6_reconcile.service import execute as reconcile
from app.modules.m7_batches.service import finalize
from app.modules.m7_batches.rules import validate

def run(payload):
    started=time.perf_counter();params=validate(payload.get('params',{}),{})
    raw,i=intake(payload);c=contract(i['rows']);m=model(c['rows']);a=calculate(m)
    q=quarantine(i['quarantine']+c['quarantine']+m['quarantine']+a['quarantine'],payload.get('reason'))
    r=reconcile(i,m,a,q);info,b=finalize(raw,params,time.perf_counter()-started,r)
    return {'intake':i,'contract':c,'model':{k:v for k,v in m.items() if k not in ('orders','sale_events','returns')},'calculate':{k:v for k,v in a.items() if k!='state'},'quarantine':q,'reconcile':r,'manifest':info,'batches':b}
