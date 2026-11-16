from .rules import verify

def execute(intake,model,calculation,quarantine):
    check=verify(model,calculation);accepted=len(model['sale_events'])+calculation['accepted'];isolated=quarantine['count'];delta=intake['input']-accepted-isolated
    return check|{'rows':calculation['accounts'],'input':intake['input'],'accepted':accepted,'isolated':isolated,'row_delta':delta,'balanced':check['balanced'] and delta==0}
