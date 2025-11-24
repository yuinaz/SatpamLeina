from __future__ import annotations

from discord.ext import commands

import asyncio, json, subprocess, sys, os, time
from typing import List, Dict, Any
import discord
from discord.ext import tasks
from satpambot.config.runtime import cfg
from .selfheal_router import send_selfheal

def _is_render_env() -> bool:
    return any(os.environ.get(k) for k in ('RENDER','RENDER_SERVICE_ID','RENDER_EXTERNAL_URL'))

def pip_list_outdated() -> List[Dict[str, Any]]:
    try:
        out = subprocess.check_output([sys.executable,'-m','pip','list','--outdated','--format=json'], text=True)
        return json.loads(out)
    except Exception:
        return []

def _crucial_set() -> set[str]:
    base = set([x.strip().lower() for x in str(cfg('CRUCIAL_PACKAGES', 'groq,discord.py,numpy,pandas,Pillow')).split(',') if x.strip()])
    return base

def _approved_once() -> set[str]:
    arr = cfg('UPD_APPROVE_ONCE', []) or []
    return set([str(x).lower() for x in arr])

def _classify(outdated: List[Dict[str, Any]]):
    crucial = _crucial_set(); approved = _approved_once()
    ts = int(cfg('UPD_APPROVE_TS', 0) or 0)
    if ts and (time.time() - ts) > 3600:
        cfg('UPD_APPROVE_ONCE', []); cfg('UPD_APPROVE_TS', 0); approved = set()
    cand, held = [], []
    for i in outdated:
        name = i['name']; lname = name.lower()
        cur = i.get('version','?'); new = i.get('latest_version','?')
        reason = None
        if _is_render_env(): reason = 'render-report-only'
        if lname == 'groq' and (str(new).split('.')[0] != '1'): reason = 'major-pin (groq v1 adapter)'
        if lname in crucial and lname not in approved: reason = (reason + ', crucial') if reason else 'crucial'
        if reason:
            held.append(f"{name}: {cur} → {new}  [{reason}]")
        else:
            cand.append('groq>=1,<2' if lname == 'groq' else f"{name}=={new}")
    return cand, held

def _mk_embed(title: str, desc: str = '', color: int = 0x3498db, fields=None):
    em = discord.Embed(title=title, description=desc or discord.Embed.Empty, color=color)
    if fields:
        for name, value, inline in fields:
            em.add_field(name=name, value=value or '-', inline=inline)
    return em

class AutoUpdateManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        await asyncio.sleep(3)
        outs = pip_list_outdated()
        cand, held = _classify(outs)
        em = _mk_embed('Startup — Update Report', 'Render: report-only' if _is_render_env() else 'MiniPC: auto-apply non-critical', 0xf5b041, [
            ('Apply candidates', '\n- ' + '\n- '.join(cand or ['(none)']), False),
            ('Held updates', '\n- ' + '\n- '.join(held or ['(none)']), False),
            ('Total Outdated', str(len(outs)), True),
        ])
        await send_selfheal(self.bot, em)

    @tasks.loop(hours=96)
    async def periodic_check(self):
        outs = pip_list_outdated()
        cand, held = _classify(outs)
        em = _mk_embed('AutoUpdate — Report', 'Render: report-only' if _is_render_env() else 'MiniPC: auto-apply non-critical', 0xf5b041, [
            ('Apply candidates', '\n- ' + '\n- '.join(cand or ['(none)']), False),
            ('Held updates', '\n- ' + '\n- '.join(held or ['(none)']), False),
            ('Total Outdated', str(len(outs)), True),
        ])
        await send_selfheal(self.bot, em)
async def setup(bot): await bot.add_cog(AutoUpdateManager(bot))