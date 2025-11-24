from __future__ import annotations

# a00_warn_downgrade_overlay.py

from discord.ext import commands
import logging, re

class _MsgFilter(logging.Filter):
    DROP_PAT = [
        re.compile(r"no executable method to wrap", re.I),
        re.compile(r"target ban command tidak ditemukan", re.I),
        re.compile(r"PyNaCl is not installed, voice will NOT be supported", re.I),
        re.compile(r"No direct XP method found\. Will dispatch events", re.I),
    ]
    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.getMessage())
        for pat in self.DROP_PAT:
            if pat.search(msg):
                # downgrade to DEBUG
                if record.levelno >= logging.WARNING:
                    record.levelno = logging.DEBUG
                    record.levelname = "DEBUG"
                break
        return True

class WarnDowngrade(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        # Global filters
        root = logging.getLogger()
        root.addFilter(_MsgFilter())
        # Discord client voice warning → silence to ERROR
        logging.getLogger("discord.client").setLevel(logging.ERROR)
async def setup(bot: commands.Bot):
    await bot.add_cog(WarnDowngrade(bot))