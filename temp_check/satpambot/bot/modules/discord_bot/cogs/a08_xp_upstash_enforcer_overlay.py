# -*- coding: utf-8 -*-
"""
a08_xp_upstash_enforcer_overlay
- Pastikan backend XP = Upstash saat env tersedia; kalau tidak, warning besar.
- Opsional migrasi dari file ke Upstash saat boot pertama (ENV XP_MIGRATE_FILE_TO_UPSTASH=1).
- Non-blocking; akan skip jika env tidak lengkap.
"""
from discord.ext import commands

import os, json, logging, urllib.request, urllib.error, pathlib, asyncio

log=logging.getLogger(__name__)

BASE=(os.getenv("UPSTASH_REDIS_REST_URL","").rstrip("/"))
TOK=os.getenv("UPSTASH_REDIS_REST_TOKEN","")
ENABLE=os.getenv("UPSTASH_ENABLE", os.getenv("XP_UPSTASH_ENABLED","1"))
HDR={"Authorization": f"Bearer {TOK}"} if TOK else {}

FILE_PATH=pathlib.Path("data/learn/tk_xp.json")

def _get(k):
    if not (BASE and TOK): return None
    try:
        req=urllib.request.Request(f"{BASE}/get/{k}", headers=HDR)
        with urllib.request.urlopen(req, timeout=5) as r:
            import json as j; return j.loads(r.read().decode()).get("result")
    except Exception:
        return None

def _set(k,v):
    if not (BASE and TOK): return False
    try:
        req=urllib.request.Request(f"{BASE}/set/{k}/{v}", headers=HDR, method="POST")
        with urllib.request.urlopen(req, timeout=5) as r:
            import json as j; return (j.loads(r.read().decode()).get("result")=="OK")
    except Exception:
        return False

def _migrate_file_to_upstash():
    if not FILE_PATH.exists(): return False
    try:
        data=json.loads(FILE_PATH.read_text("utf-8"))
        senior = data.get("senior_total") or data.get("senior_total_xp")
        tk     = data.get("tk_total")
        ok1= _set("xp:bot:senior_total", str(senior if senior is not None else ""))
        ok2= _set("xp:bot:tk_total", str(tk if tk is not None else ""))
        if ok1 or ok2:
            log.info("[xp-enforcer] migrated file -> upstash (senior=%s tk=%s)", senior, tk)
            return True
    except Exception as e:
        log.warning("[xp-enforcer] migrate fail: %r", e)
    return False

class XPEnforcer(commands.Cog):
    def __init__(self,bot): self.bot=bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not ENABLE or ENABLE=="0":
            log.warning("[xp-enforcer] Upstash disabled by env; backend may be FILE.")
            return
        if not (BASE and TOK):
            log.warning("[xp-enforcer] Upstash env missing; set UPSTASH_REDIS_REST_URL/TOKEN")
            return
        # sanity ping
        v=_get("xp:bot:senior_total")
        if v is None and os.getenv("XP_MIGRATE_FILE_TO_UPSTASH","0")=="1":
            _migrate_file_to_upstash()
        log.info("[xp-enforcer] backend target=upstash url=%s (key senior_total=%s)", BASE, v)

async def setup(bot): await bot.add_cog(XPEnforcer(bot))