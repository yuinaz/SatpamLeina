from __future__ import annotations

from discord.ext import commands
import logging
import discord

from satpambot.config.local_cfg import cfg_int

log = logging.getLogger(__name__)

def _ids_from_cfg():
    return set(filter(bool, [
        cfg_int("LOG_CHANNEL_ID", 0),
        cfg_int("PUBLIC_REPORT_CHANNEL_ID", 0),
        cfg_int("PROGRESS_CHANNEL_ID", 0),
    ]))

class LogChannelRelaxer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.protected = _ids_from_cfg()

    async def cog_load(self):
        self._patch_delete()
        self._patch_purge()
        log.info("[log_relax] protect channels=%s", sorted(self.protected))

    def _patch_delete(self):
        orig = discord.message.Message.delete
        async def safe_delete(msg: discord.Message, *a, **kw):
            try:
                if msg.channel and getattr(msg.channel, "id", None) in self.protected:
                    return
            except Exception:
                pass
            return await orig(msg, *a, **kw)
        discord.message.Message.delete = safe_delete

    def _patch_purge(self):
        def wrap_purge(cls):
            if not hasattr(cls, "purge"):
                return
            orig = cls.purge
            async def safe_purge(self, *a, **kw):
                try:
                    if getattr(self, "id", None) in self.protected:
                        return []
                except Exception:
                    pass
                return await orig(self, *a, **kw)
            setattr(cls, "purge", safe_purge)
        from discord import TextChannel, Thread
        for c in (TextChannel, Thread):
            wrap_purge(c)
async def setup(bot: commands.Bot):
    await bot.add_cog(LogChannelRelaxer(bot))