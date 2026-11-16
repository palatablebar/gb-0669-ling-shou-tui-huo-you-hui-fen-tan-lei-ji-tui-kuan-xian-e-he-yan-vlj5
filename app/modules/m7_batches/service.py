import csv
import io
import json
from app.manifest import manifest

def finalize(raw,params,elapsed,summary):
    info=manifest(raw,params,elapsed)
    return info,{'rows':[{'run_id':info['run_id'],'sha256':info['sha256'],'version':info['rule_version'],'elapsed_ms':info['elapsed_ms'],'status':'通过' if summary['balanced'] else '待复核'}],'params':params}

def evidence_csv(result):
    out=io.StringIO(newline='')
    writer=csv.writer(out)
    writer.writerow(['批次','来源行','原因码','说明','原值'])
    for row in result['quarantine']['rows']:
        values=[result['manifest']['run_id'],row['line'],row['code'],row['detail'],json.dumps(row['raw'],ensure_ascii=False,sort_keys=True)]
        writer.writerow(["'"+v if isinstance(v,str) and v[:1] in '=+-@' else v for v in values])
    if not result['quarantine']['rows']:writer.writerow([result['manifest']['run_id'],'','PASS','无隔离记录',''])
    return '\ufeff'+out.getvalue()
