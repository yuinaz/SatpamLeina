import os, asyncio, json, sys
try: import httpx
except Exception as e: 
    print("ERROR: httpx not installed -> pip install httpx", file=sys.stderr); raise
def getenv_first(*names, default=""):
    for n in names:
        v = os.getenv(n, "")
        if v: return v
    return default
BASE = getenv_first("UPSTASH_REDIS_REST_URL", "UPSTASH_REST_URL").strip().rstrip("/")
TOKEN = getenv_first("UPSTASH_REDIS_REST_TOKEN", "UPSTASH_REST_TOKEN").strip()
def _fail(msg, code=2): print(f"[xp-smoke] {msg}", file=sys.stderr); sys.exit(code)
def _check_env():
    if not BASE: _fail("Missing UPSTASH_REDIS_REST_URL (or UPSTASH_REST_URL).")
    if not (BASE.startswith("http://") or BASE.startswith("https://")): _fail(f"Invalid URL: {BASE}")
    if not TOKEN: _fail("Missing UPSTASH_REDIS_REST_TOKEN (or UPSTASH_REST_TOKEN).")
async def pipeline(cmds):
    headers={"Authorization": f"Bearer {TOKEN}"}
    url=f"{BASE}/pipeline"
    async with httpx.AsyncClient(timeout=30) as cli:
        r=await cli.post(url, headers=headers, json=cmds)
        if r.status_code>=400: raise RuntimeError(f"HTTP {r.status_code}: {r.text[:400]}")
        return r.json()
def _res_val(item): 
    return item.get("result") if isinstance(item, dict) else None
async def main():
    _check_env()
    cmds=[["GET","xp:store"], ["GET","xp:bot:senior_total"], ["GET","xp:ladder:TK"]]
    try:
        data=await pipeline(cmds); print("[xp-smoke] pipeline OK")
        store_raw=_res_val(data[0]) if len(data)>0 else None
        try: store=json.loads(store_raw or "{}")
        except Exception: store={}
        print("  - xp:bot:senior_total:", _res_val(data[1]) if len(data)>1 else None)
        print("  - xp:ladder:TK:", _res_val(data[2]) if len(data)>2 else None)
        print("  - store keys:", ", ".join(sorted(store.keys())[:8]) or "(empty)")
    except Exception as e:
        print("[xp-smoke] ERROR:", repr(e), file=sys.stderr); sys.exit(1)
if __name__=="__main__": asyncio.run(main())
