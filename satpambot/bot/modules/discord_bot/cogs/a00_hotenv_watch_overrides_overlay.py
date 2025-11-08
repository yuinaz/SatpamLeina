import os, logging, pathlib, time
log=logging.getLogger(__name__)
FILES=os.getenv('HOTENV_WATCH_FILES','data/config/overrides.render-free.json,.env').split(',')
DELAY=int(os.getenv('HOTENV_DEBOUNCE_MS','1200'))/1000.0
def iter_paths():
    for f in FILES:
        p=pathlib.Path(f.strip())
        if p.exists(): yield p
def watch(callback):
    mtimes={}
    while True:
        changed=False
        for p in iter_paths():
            try: m=p.stat().st_mtime
            except Exception: continue
            if mtimes.get(p)!=m:
                mtimes[p]=m; changed=True
        if changed:
            try: callback()
            except Exception as e: log.warning('[hotenv-watch] cb failed: %r', e)
        time.sleep(DELAY)
