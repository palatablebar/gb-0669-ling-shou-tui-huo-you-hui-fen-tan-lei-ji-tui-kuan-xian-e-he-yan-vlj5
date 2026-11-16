import os
import json
import sqlite3
from pathlib import Path
from app.errors import DomainError
from app.config import VERSION

def connect():
    path=Path(os.getenv('DB_PATH','state.sqlite'))
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=15)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, payload TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1, reviewed INTEGER NOT NULL DEFAULT 0, created TEXT DEFAULT CURRENT_TIMESTAMP)')
    return db

def save(result):
    rid=result['manifest']['run_id']
    with connect() as db:
        cur=db.execute('INSERT OR IGNORE INTO runs(id,payload) VALUES(?,?)',(rid,json.dumps(result,ensure_ascii=False)))
        created=cur.rowcount==1
    return read(rid)|{'created':created}

def read(rid):
    with connect() as db: row=db.execute('SELECT * FROM runs WHERE id=?',(rid,)).fetchone()
    if not row: raise DomainError('RUN_MISSING','批次不存在',404)
    payload=json.loads(row['payload'])
    rule_version=payload.get('manifest',{}).get('rule_version','')
    stale=bool(rule_version and rule_version!=VERSION)
    return payload|{'revision':row['revision'],'reviewed':bool(row['reviewed']),'created_at':row['created'],'stale':stale,'current_version':VERSION}

def history():
    with connect() as db: rows=db.execute('SELECT id,payload,revision,reviewed,created FROM runs ORDER BY created DESC,id DESC LIMIT 100').fetchall()
    out=[]
    for r in rows:
        rule_version=json.loads(r['payload']).get('manifest',{}).get('rule_version','')
        out.append({'id':r['id'],'revision':r['revision'],'reviewed':bool(r['reviewed']),'created':r['created'],'stale':bool(rule_version and rule_version!=VERSION)})
    return out

def review(rid, revision):
    with connect() as db:
        row=db.execute('SELECT payload,revision FROM runs WHERE id=?',(rid,)).fetchone()
        if not row: raise DomainError('RUN_MISSING','批次不存在',404)
        payload=json.loads(row['payload'])
        rule_version=payload.get('manifest',{}).get('rule_version','')
        if rule_version and rule_version!=VERSION:
            raise DomainError('RULE_STALE',f'规则已更新至 {VERSION}，原结果失效，请重算后再复核',409)
        if not payload['reconcile']['balanced']: raise DomainError('UNBALANCED','对账未通过，先处理差异',409)
        cur=db.execute('UPDATE runs SET reviewed=1,revision=revision+1 WHERE id=? AND revision=?',(rid,revision))
        if cur.rowcount!=1: raise DomainError('STALE_VERSION','版本已变更，请重新加载',409)
    return read(rid)
