# Auto-generated helper: Upstash NX/EX guard for QnA poster
import os, json, urllib.request, time
def _env(k, d=None):
    v=os.getenv(k); return v if v not in (None,"") else d
def _pipe(cmds):
    base=_env("UPSTASH_REDIS_REST_URL"); tok=_env("UPSTASH_REDIS_REST_TOKEN")
    if not base or not tok: return None
    body=json.dumps(cmds).encode("utf-8")
    req=urllib.request.Request(f"{base}/pipeline", method="POST", data=body)
    req.add_header("Authorization", f"Bearer {tok}"); req.add_header("Content-Type","application/json")
    with urllib.request.urlopen(req, timeout=3.0) as r:
        return json.loads(r.read().decode("utf-8","ignore"))
def _claim_qna_slot(ttl: int) -> bool:
    try:
        r = _pipe([["SET","qna:emit_guard",str(int(time.time())),"EX",str(ttl),"NX"]])
        return bool(r and isinstance(r,list) and r[0].get("result")=="OK")
    except Exception:
        return True
