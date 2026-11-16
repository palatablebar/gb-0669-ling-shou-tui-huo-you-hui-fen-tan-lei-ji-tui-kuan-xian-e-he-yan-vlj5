from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from importlib import import_module
from app.config import TITLE,ROOT,PAGES
from app.errors import DomainError
from app import store
from app.web import render
app=FastAPI(title=TITLE)
app.mount('/static',StaticFiles(directory=ROOT/'app/static'),name='static')
for i,(slug,_) in enumerate(PAGES,1):app.include_router(import_module(f'app.modules.m{i}_{slug}.handler').router)

@app.exception_handler(DomainError)
async def domain_error(request,exc):return JSONResponse({'code':exc.code,'detail':exc.detail},status_code=exc.status)

@app.get('/healthz')
def health():return {'status':'ok'}

@app.get('/api/history')
def history():return store.history()

@app.get('/api/run/{rid}')
def run_read(rid:str):return store.read(rid)

@app.post('/api/review/{rid}')
def review(rid:str,payload:dict):
    revision=payload.get('revision')
    if not isinstance(revision,int):raise DomainError('REVISION','请提交整数版本')
    return store.review(rid,revision)

@app.get('/api/export/{rid}')
def evidence(rid:str):
    from app.modules.m7_batches.service import evidence_csv
    return Response(evidence_csv(store.read(rid)),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="evidence.csv"'})

@app.get('/')
def home():return RedirectResponse('/intake')

@app.get('/{page}')
def page(request:Request,page:str,run:str|None=None):
    if page not in dict(PAGES):raise DomainError('PAGE_MISSING','页面不存在',404)
    return render(request,page,run)
