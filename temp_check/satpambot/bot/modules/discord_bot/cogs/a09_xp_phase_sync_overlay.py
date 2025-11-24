# -*- coding: utf-8 -*-
from discord.ext import commands

import os, json, urllib.request, asyncio

BASE=(os.getenv("UPSTASH_REDIS_REST_URL","").rstrip("/")); TOK=os.getenv("UPSTASH_REDIS_REST_TOKEN","")
HDR={"Authorization": f"Bearer {TOK}"} if TOK else {}
def _get(k):
    if not (BASE and TOK): return None
    try:
        req=urllib.request.Request(f"{BASE}/get/{k}", headers=HDR); 
        with urllib.request.urlopen(req, timeout=5) as r:
            import json as _j; return _j.loads(r.read().decode()).get("result")
    except Exception: return None
def _set(k,v):
    if not (BASE and TOK): return False
    try:
        req=urllib.request.Request(f"{BASE}/set/{k}/{v}", headers=HDR, method="POST")
        with urllib.request.urlopen(req, timeout=5) as r:
            import json as _j; return _j.loads(r.read().decode()).get("result")=="OK"
    except Exception: return False
class Phase(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @commands.Cog.listener()
    async def on_ready(self):
        sj=_get("learning:status_json"); ph=_get("learning:phase")
        try: lab=(json.loads(sj) if isinstance(sj,str) else sj).get("label")
        except Exception: lab=None
        want="kuliah" if isinstance(lab,str) and lab.upper().startswith("KULIAH") else None
        if want:
            try: cur=(json.loads(ph) if isinstance(ph,str) else ph or {}).get("phase")
            except Exception: cur=None
            if cur!=want: _set("learning:phase", json.dumps({"phase":want}))

async def setup_async(bot): await bot.add_cog(Phase(bot))

def setup(bot):
    try:
        loop = asyncio.get_event_loop()
        if loop and loop.is_running():
            return loop.create_task(setup_async(bot))
    except Exception:
        pass
    return asyncio.run(setup_async(bot))