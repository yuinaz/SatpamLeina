from __future__ import annotations

from discord.ext import commands
import logging, asyncio
from typing import Optional
import discord

from satpambot.config.local_cfg import cfg, cfg_int

log = logging.getLogger(__name__)
TITLES = {t.strip() for t in str(cfg("STATUS_COALESCE_TITLES","") or "Periodic Status").split(",") if t.strip()}
PIN_DELAY = int(cfg_int("STATUS_PIN_DELAY_MS", 200) or 200)

def _find_title(msg: discord.Message) -> Optional[str]:
    try:
        if not msg.embeds: return None
        for e in msg.embeds:
            if (t := (e.title or "")).strip() in TITLES:
                return t.strip()
        return None
    except Exception:
        return None

async def _enforce_pin(msg: discord.Message, title: str):
    try:
        # pin new message
        await asyncio.sleep(PIN_DELAY/1000.0)
        await msg.pin(reason=f"pin:{title}")
        # unpin older status messages in the same channel
        pins = await msg.channel.pins()
        for p in pins:
            if p.id == msg.id: 
                continue
            if _find_title(p) == title:
                try: await p.unpin(reason="rotate status pin")
                except Exception: pass
        log.info("[status_pin] ensured pin for '%s' in #%s", title, getattr(msg.channel, 'name', '?'))
    except Exception as e:
        log.debug("[status_pin] pin failed: %r", e)

class _StatusPinEnforcer(commands.Cog):
    def __init__(self, bot): self.bot = bot
    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        try:
            if not m or not m.author or not m.author.bot: 
                return
            title = _find_title(m)
            if not title: 
                return
            await _enforce_pin(m, title)
        except Exception:
            pass
async def setup(bot): 
    await bot.add_cog(_StatusPinEnforcer(bot))
    # Suggest a long coalesce window so edits happen instead of new messages
    try:
        from satpambot.bot.modules.discord_bot.cogs import a06_status_coalescer_overlay as co
        if hasattr(co, "WINDOW") and co.WINDOW < 43200:  # 12h
            co.WINDOW = 43200
            log.info("[status_pin] extended coalesce window to %ss", co.WINDOW)
    except Exception:
        pass