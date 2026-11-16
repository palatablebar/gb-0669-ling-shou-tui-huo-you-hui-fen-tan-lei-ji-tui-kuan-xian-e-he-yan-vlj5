from .rules import classify,filter_rows

def execute(rows,code=None):
    selected=filter_rows(rows,code)
    return {'count':len(rows),'selected':len(selected),'reasons':classify(rows),'rows':selected,'recoverable':sum(r['code'] in ('NULL_VALUE','NUMBER','COLUMN_COUNT') for r in selected)}
