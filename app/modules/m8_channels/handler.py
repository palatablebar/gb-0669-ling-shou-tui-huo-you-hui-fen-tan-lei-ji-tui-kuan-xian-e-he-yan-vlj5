from fastapi import APIRouter, Body
from app.errors import DomainError
router = APIRouter(prefix='/api/channels', tags=['channels'])

@router.get('/queue')
def read_queue(channel: str | None = None):
    from app.modules.m8_channels.service import queue
    return queue(channel)

@router.post('/submit')
def submit(payload: dict = Body(...)):
    from app.modules.m8_channels.service import submit as run_submit
    return run_submit(payload)

@router.post('/import')
def import_catalog(payload: dict = Body(...)):
    from app.modules.m8_channels.service import import_catalog as run_import
    return run_import(payload)

@router.post('/recover')
def recover():
    from app.modules.m8_channels.service import recover as run_recover
    return run_recover()
