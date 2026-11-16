from fastapi import APIRouter, Body
from app.errors import DomainError
router = APIRouter(prefix='/api/intake', tags=['intake'])

@router.get('')
def sample():
    from app.pipeline import run
    return run({'sample':'dirty'})['intake']

@router.post('')
def execute(payload: dict = Body(default={})):
    if not isinstance(payload.get('params',{}),dict):raise DomainError('PARAMS','参数必须为对象')
    from app.pipeline import run
    result=run(payload)
    if 'intake'=='batches':
        from app.store import save
        return save(result)
    return result['intake']
