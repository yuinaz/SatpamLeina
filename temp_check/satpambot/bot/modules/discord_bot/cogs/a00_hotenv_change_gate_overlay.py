import logging
log=logging.getLogger(__name__)
def _diff(a:dict,b:dict)->dict:
    d={}
    for k in set((a or {}).keys())|set((b or {}).keys()):
        if (a or {}).get(k)!=(b or {}).get(k): d[k]=[(a or {}).get(k),(b or {}).get(k)]
    return d
def apply_change(old_env:dict,new_env:dict)->bool:
    diff=_diff(old_env,new_env)
    if not diff:
        log.warning('[hotenv-change] ignored hotenv_reload (no config change)')
        return False
    log.info('[hotenv-change] %d keys changed', len(diff)); 
    return True
