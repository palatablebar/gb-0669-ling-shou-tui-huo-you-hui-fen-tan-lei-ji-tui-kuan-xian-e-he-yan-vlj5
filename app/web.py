from fastapi.templating import Jinja2Templates
from app.config import ROOT,TITLE,SHORT,PAGES,VERSION
from app import store
from app.pipeline import run
templates=Jinja2Templates(directory=ROOT/'app/templates')

def render(request,page,rid=None):
    result=store.read(rid) if rid else store.save(run({'sample':'dirty'}))
    return templates.TemplateResponse(request=request,name=f'{page}.html',context={'title':TITLE,'short':SHORT,'pages':PAGES,'page':page,'page_title':dict(PAGES)[page],'version':VERSION,'result':result,'section':result[page],'history':store.history()})
