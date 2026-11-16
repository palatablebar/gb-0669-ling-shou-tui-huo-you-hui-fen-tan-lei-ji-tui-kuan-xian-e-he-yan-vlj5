from fastapi.templating import Jinja2Templates
from app.config import ROOT,TITLE,SHORT,PAGES,VERSION
from app import store
from app.pipeline import run
templates=Jinja2Templates(directory=ROOT/'app/templates')

def render(request,page,rid=None):
    if page=='channels':
        from app.modules.m8_channels.service import queue
        result=store.save(run({'sample':'contest'})) if not rid else store.read(rid)
        section=queue()
        return templates.TemplateResponse(request=request,name='channels.html',context={'title':TITLE,'short':SHORT,'pages':PAGES,'page':page,'page_title':dict(PAGES)[page],'version':VERSION,'result':result,'section':section,'history':store.history()})
    result=store.read(rid) if rid else store.save(run({'sample':'dirty'}))
    return templates.TemplateResponse(request=request,name=f'{page}.html',context={'title':TITLE,'short':SHORT,'pages':PAGES,'page':page,'page_title':dict(PAGES)[page],'version':VERSION,'result':result,'section':result[page],'history':store.history()})
