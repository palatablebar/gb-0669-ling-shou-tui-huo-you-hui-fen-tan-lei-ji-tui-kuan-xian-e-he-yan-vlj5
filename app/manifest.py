import hashlib
import json
from app import config

def digest(raw, params):
    content = json.dumps({'sha256':hashlib.sha256(raw).hexdigest(),'params':params,'version':config.VERSION},sort_keys=True,separators=(',',':'),ensure_ascii=False)
    return hashlib.sha256(content.encode()).hexdigest()

def manifest(raw, params, elapsed):
    return {'run_id':digest(raw,params)[:20], 'sha256':hashlib.sha256(raw).hexdigest(),'rule_version':config.VERSION, 'params':params, 'elapsed_ms':round(elapsed*1000,3)}
