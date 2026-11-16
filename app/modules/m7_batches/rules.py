from app.errors import DomainError

def validate(params,defaults):
    unknown=set(params)-set(defaults)
    if unknown:raise DomainError('UNKNOWN_PARAM','未知参数：'+','.join(sorted(unknown)))
    result=defaults|params
    for key,value in result.items():
        if isinstance(defaults[key],int) and (type(value)!=int or value<1 or value>10000):raise DomainError('PARAM_RANGE','参数范围为1至10000')
    return result
