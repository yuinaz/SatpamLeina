# -*- coding: utf-8 -*-
"""
a11_status_unified_overlay
- Satu embed untuk Maintenance + Self-Heal (multi-section).
- Anti-spam: coalesce update <= window_sec per channel (default 60s).
- Pin/Upsert via EmbedScribe.upsert (async-safe; guarded oleh post_shim_v2/v3).
- Tanpa mengubah command lama; hanya menyediakan util dan listener sederhana.
Env:
  STATUS_UNIFIED_WINDOW_SEC=60
  STATUS_CHANNEL_ID= (opsional, channel default)
"""
from discord.ext import commands
import os, time, logging, asyncio, importlib

log=logging.getLogger(__name__)

def _get_embed_scribe():
    mod = importlib.import_module("satpambot.bot.utils.embed_scribe")
    return getattr(mod, "EmbedScribe")

def _now(): return int(time.time())

class StatusUnified(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.window = int(os.getenv("STATUS_UNIFIED_WINDOW_SEC", "60") or "60")
        self.last = {}  # key=(guild_id, channel_id) -> (ts, key)
        self.es = _get_embed_scribe()(bot)

    async def upsert_sections(self, channel, key, sections, pin=True):
        """sections: dict[str, str] -> digabung jadi satu embed"""
        try:
            import discord
            e = discord.Embed(title="Maintenance / Self-Heal", colour=discord.Colour.blurple())
            for name, val in sections.items():
                if not val: continue
                e.add_field(name=name, value=str(val)[:1024], inline=False)
            await self.es.upsert(channel, key, e, pin=pin)
        except Exception as e:
            log.warning("[status-unified] upsert error: %r", e)

    async def log_note(self, channel_id: int, maintenance:str=None, note:str=None, plan:str=None, pin=True):
        ch = self.bot.get_channel(int(channel_id)) if hasattr(self.bot,"get_channel") else None
        if not ch: return False
        k = ("status-unified", str(channel_id))
        ts = _now()
        prev = self.last.get(k)
        if prev and (ts - prev[0]) < self.window:
            # coalesce: keep same key
            pass
        else:
            self.last[k] = (ts, k)
        sections = {}
        if maintenance: sections["Maintenance"] = maintenance
        if note: sections["Self-Heal Note"] = note
        if plan: sections["Self-Heal Plan"] = plan
        await self.upsert_sections(ch, "status:maintenance", sections, pin=pin)
        return True

    @commands.command(name="statuscard")
    async def statuscard_cmd(self, ctx, *, text: str = ""):
        """Manual testing: !statuscard Maintenance ok | Note ... | Plan ..."""
        parts = [p.strip() for p in (text or "").split("|")]
        get = lambda i: parts[i] if i < len(parts) and parts[i] else None
        await self.log_note(
            os.getenv("STATUS_CHANNEL_ID") or ctx.channel.id,
            maintenance=get(0), note=get(1), plan=get(2), pin=True)
async def setup(bot):
    await bot.add_cog(StatusUnified(bot))