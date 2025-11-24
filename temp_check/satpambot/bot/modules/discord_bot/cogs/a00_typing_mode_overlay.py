# a00_typing_mode_overlay.py
from __future__ import annotations
import os, logging
from contextlib import asynccontextmanager
import discord
from discord.ext import commands
log = logging.getLogger(__name__)
class TypingMode(commands.Cog):
    def __init__(self, bot: commands.Bot):
        mode = (os.getenv("QNA_TYPING_MODE") or "short").strip().lower()
        if getattr(discord.abc.Messageable, "_typing_mode_patched", False):
            log.info("[typing-mode] already patched")
            return
        @asynccontextmanager
        async def _noop(_self): yield
        @asynccontextmanager
        async def _pulse(_self):
            try: await _self.trigger_typing()
            except Exception: pass
            yield
        if mode == "off":
            discord.abc.Messageable.typing = _noop  # type: ignore
            discord.abc.Messageable._typing_mode_patched = True  # type: ignore
            log.warning("[typing-mode] off")
        elif mode == "short":
            discord.abc.Messageable.typing = _pulse  # type: ignore
            discord.abc.Messageable._typing_mode_patched = True  # type: ignore
            log.warning("[typing-mode] short")
        else:
            log.warning("[typing-mode] on (original)")
async def setup(bot: commands.Bot):
    await bot.add_cog(TypingMode(bot))
