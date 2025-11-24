# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json, asyncio, logging, urllib.request, urllib.error
from typing import Any, Tuple, List
try:
    from discord.ext import commands  # type: ignore
except Exception:
    commands = object  # type: ignore

log = logging.getLogger(__name__)

S_NAMES = ("S1","S2","S3","S4","S5","S6","S7","S8")
S_TH = (0,19000,35000,58000,70000,96500,158000,220000,262500)

def _env_pick(name: str) -> str | None:
    if name == "UPSTASH_REST_URL":
        return (os.getenv("UPSTASH_REDIS_REST_URL") or os.getenv("UPSTASH_REST_URL") or "").rstrip("/") or None
    if name == "UPSTASH_REST_TOKEN":
        return (os.getenv("UPSTASH_REDIS_REST_TOKEN") or os.getenv("UPSTASH_REST_TOKEN") or "") or None
    return os.getenv(name)

def _to_int(x)->int:
    try: return int(float(str(x).strip()))
    except Exception: return 0

def _calc_kuliah(total:int)->Tuple[str,str,dict]:
    idx=0
    for i,th in enumerate(S_TH):
        if total>=th: idx=i
    cur=S_TH[idx]; nxt=S_TH[idx] if idx==len(S_TH)-1 else S_TH[idx+1]
    if nxt<=cur: pct=100.0; rem=0
    else: pct=round(max(0.0,(total-cur)/float(nxt-cur)*100.0),1); rem=max(0,nxt-total)
    label=f"KULIAH-{S_NAMES[idx]}"; status=f"{label} ({pct}%)"
    payload={"label":label,"percent":pct,"remaining":rem,"senior_total":total}
    return label, status, payload

def _http_pipeline(cmds: List[List[str]]):
    base=_env_pick("UPSTASH_REST_URL"); tok=_env_pick("UPSTASH_REST_TOKEN")
    if not base or not tok: return (0,"UPSTASH env missing")
    req=urllib.request.Request(f"{base}/pipeline",
        data=json.dumps(cmds).encode(), method="POST",
        headers={"Authorization":f"Bearer {tok}","Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            body=r.read().decode()
            try: return (r.getcode(), json.loads(body))
            except Exception: return (r.getcode(), body)
    except urllib.error.HTTPError as e:
        try: body=e.read().decode()
        except Exception: body=str(e)
        return (e.code, body)
    except Exception as e:
        return (-1, str(e))

async def _heal_once():
    base=_env_pick("UPSTASH_REST_URL"); tok=_env_pick("UPSTASH_REST_TOKEN")
    if not base or not tok:
        log.warning("[a08-runtime] UPSTASH env missing; skip"); return
    keyA=os.getenv("XP_SENIOR_KEY") or "xp:bot:senior_total"; keyB=None
    code,res=_http_pipeline([["GET",keyA],["GET","learning:status"],["GET","learning:status_json"]])
    if code<=0 or not isinstance(res,list) or len(res)<3:
        log.warning("[a08-runtime] read failed: %s %s", code, res); return
    A=_to_int(res[0].get("result"))
    s_raw=(res[1].get("result") or "")
    j_raw=(res[2].get("result") or "{}")
    total=A
    label,status,payload=_calc_kuliah(total)
    need=False
    try:
        lbl_s=(s_raw.split(" ",1)[0] if s_raw else ""); lbl_j=json.loads(j_raw).get("label","")
        if lbl_s!=label or lbl_j!=label: need=True
    except Exception: need=True
    if not need:
        log.info("[a08-runtime] consistent already: %s", label); return
    cmds=[["SET",keyA,str(total)],
          ["SET","learning:status",status],
          ["SET","learning:status_json", json.dumps(payload,separators=(',',':'))]]
    code2,res2=_http_pipeline(cmds)
    if 200<=code2<300: log.info("[a08-runtime] fixed -> %s (total=%s)", label, total)
    else: log.warning("[a08-runtime] write failed: %s %s", code2, res2)

class KuliahStageResetRuntimeOverlay(commands.Cog if commands!=object else object):
    def __init__(self, bot=None): self.bot=bot; self._task=None
    @getattr(commands,"Cog",object).listener()
    async def on_ready(self):
        if os.getenv("A08_RUNTIME_DISABLE"): 
            log.info("[a08-runtime] disabled"); return
        if self._task is None:
            self._task=asyncio.create_task(self._once())
    async def _once(self):
        await asyncio.sleep(2.0)
        try: await _heal_once()
        except Exception as e: log.exception("[a08-runtime] error: %s", e)

def setup(bot):
    try:
        bot.add_cog(KuliahStageResetRuntimeOverlay(bot)); log.info("✅ Loaded cog (sync): %s", __name__)
    except Exception as e:
        log.exception("Failed to load (sync): %s", e)

async def setup(bot):
    try:
        await bot.add_cog(KuliahStageResetRuntimeOverlay(bot)); log.info("✅ Loaded cog (async): %s", __name__)
    except Exception as e:
        log.exception("Failed to load (async): %s", e)
