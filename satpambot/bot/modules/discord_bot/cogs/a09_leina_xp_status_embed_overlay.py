
from __future__ import annotations
import os, json, asyncio, logging
from typing import Optional, Dict, Any
from discord.ext import commands
from satpambot.bot.modules.discord_bot.helpers.task_tools import create_task_any

log = logging.getLogger(__name__)

def _num(x, default=0):
    try:
        return int(float(x))
    except Exception:
        return default

def _percent(cur: int, req: int) -> float:
    if req <= 0: return 0.0
    return round((cur/req)*100.0, 1)

def _upstash_get(key: str) -> Optional[str]:
    import urllib.request, json as _json, os
    url = os.getenv("UPSTASH_REDIS_REST_URL")
    tok = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    if not url or not tok:
        return None
    if url.endswith("/"):
        url = url[:-1]
    try:
        req = urllib.request.Request(f"{url}/get/{key}")
        req.add_header("Authorization", f"Bearer {tok}")
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode("utf-8","ignore")
            data = _json.loads(raw)
            return None if data.get("result") in (None, "null") else str(data.get("result"))
    except Exception:
        return None

def _load_local_snapshot() -> Optional[Dict[str, Any]]:
    cands = [
        "data/config/xp_stage_ladder.json",
        "data/config/xp_ladder.json",
        "data/config/xp_kuliah_ladder.json",
        "data/config/xp_work_ladder.json",
    ]
    for p in cands:
        try:
            with open(p,"r",encoding="utf-8") as f:
                j = json.load(f)
                st = j.get("stage", j)
                lab = st.get("label") or j.get("label") or "UNKNOWN"
                cur = _num(st.get("current", st.get("xp", 0)))
                req = _num(st.get("required", 0))
                return {"label": str(lab), "current": cur, "required": req, "percent": _percent(cur, req)}
        except Exception:
            continue
    return None

async def _compute_snapshot() -> Dict[str, Any]:
    lab = _upstash_get("xp:stage:label")
    cur = _upstash_get("xp:stage:current")
    req = _upstash_get("xp:stage:required")
    if lab or cur or req:
        cur_i = _num(cur); req_i = _num(req)
        return {"label": lab or "UNKNOWN", "current": cur_i, "required": req_i, "percent": _percent(cur_i, req_i)}
    snap = _load_local_snapshot() or {"label":"UNKNOWN","current":0,"required":0,"percent":0.0}
    return snap

def _build_embed_dict(s: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": "Leina Progress",
        "description": f"**{s.get('label','UNKNOWN')} — {s.get('percent',0.0)}%**\n\nPer‑Level **{s.get('current',0)} / {s.get('required',0)} XP**",
        "footer": {"text": "leina:xp_status"},
    }

class LeinaXpStatusEmbedOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.interval = max(60, int(os.getenv("XP_STATUS_INTERVAL_SEC","1200") or "1200"))
        self.ch_id = int(os.getenv("XP_STATUS_CHANNEL_ID","0") or "0")
        self.msg_id = int(os.getenv("XP_STATUS_MESSAGE_ID","0") or "0")

    async def _runner(self):
        await self.bot.wait_until_ready()
        while not getattr(self.bot, "is_closed", lambda: False)():
            try:
                await self.update_once()
            except Exception as e:
                log.debug("[xp-status] update failed: %r", e)
            await asyncio.sleep(self.interval)

    async def update_once(self):
        s = await _compute_snapshot()
        ch = self.bot.get_channel(self.ch_id) if self.ch_id else None
        if ch is None and self.ch_id:
            try:
                ch = await self.bot.fetch_channel(self.ch_id)
            except Exception:
                ch = None
        if not ch:
            return
        try:
            msg = await ch.fetch_message(self.msg_id) if self.msg_id else None
        except Exception:
            msg = None
        content_json = json.dumps({
            "xp:stage:label": s["label"],
            "xp:stage:current": s["current"],
            "xp:stage:required": s["required"],
            "xp:stage:percent": s["percent"],
        })
        try:
            if msg:
                await msg.edit(content=f"```json\n{content_json}\n```")
            else:
                await ch.send(content=f"```json\n{content_json}\n```")
        except Exception as e:
            log.debug("[xp-status] content send/edit failed: %r", e)
        try:
            import discord
            emb = discord.Embed.from_dict(_build_embed_dict(s))
            if msg:
                await msg.edit(embed=emb)
            else:
                await ch.send(embed=emb)
        except Exception as e:
            log.debug("[xp-status] embed failed: %r", e)

async def setup(bot: commands.Bot):
    cog = LeinaXpStatusEmbedOverlay(bot)
    await bot.add_cog(cog)
    if cog.ch_id:
        create_task_any(bot, cog._runner())
