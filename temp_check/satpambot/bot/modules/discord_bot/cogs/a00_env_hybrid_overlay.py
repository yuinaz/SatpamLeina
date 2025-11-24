import json, logging, os, pathlib, re
log=logging.getLogger(__name__); log.setLevel(logging.INFO)
_UPPER=re.compile(r'^[A-Z0-9_]+$')
def _read_overrides_env():
    p=pathlib.Path('data/config/overrides.render-free.json')
    if not p.is_file(): p=pathlib.Path(__file__).parents[4]/'data/config/overrides.render-free.json'
    try:
        data=json.loads(p.read_text(encoding='utf-8')); env=data.get('env',{})
        if isinstance(env,dict):
            return {k:str(v) for k,v in env.items() if isinstance(k,str) and _UPPER.match(k)}, str(p)
    except Exception: log.exception('[env-hybrid] read failed: %s', p)
    return {}, '<missing>'
def export_env():
    ov, path=_read_overrides_env(); exported=0; preserved=[]
    for k,v in (ov or {}).items():
        if k in os.environ: preserved.append(k); continue
        os.environ[k]=v; exported+=1
    log.warning('[env-hybrid] source=%s exported=%d', path, exported)
try: export_env()
except Exception: log.exception('[env-hybrid] export failed')
