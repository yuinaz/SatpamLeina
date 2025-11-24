from __future__ import annotations
from discord.ext import commands

import asyncio
from typing import Optional
import discord

COG_NAME = "XPAwardDirectMethodShim"

class XPAwardDirectMethodShim(commands.Cog):
    """Install direct XP methods on the bot instance so other cogs
    can call `bot.xp_add(...)` / `bot.award_xp(...)` without warnings.
    Internally we only *dispatch events* so your existing XP backend
    (e.g., XPDiscordBackend / XPCommand) continues to handle storage.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        async def _xp_add(member_id: int, amount: int, *, reason: Optional[str] = None,
                          channel_id: Optional[int] = None, guild_id: Optional[int] = None):
            # unify to events — no storage here
            self.bot.dispatch("xp_add", member_id, amount, reason, channel_id, guild_id)
            self.bot.dispatch("xp.award", member_id, amount, reason, channel_id, guild_id)
            self.bot.dispatch("satpam_xp", member_id, amount, reason, channel_id, guild_id)

        # expose as attributes (async funcs)
        setattr(bot, "xp_add", _xp_add)
        setattr(bot, "award_xp", _xp_add)

    def cog_unload(self):
        # clean up attributes on reload
        for attr in ("xp_add", "award_xp"):
            if hasattr(self.bot, attr):
                try:
                    delattr(self.bot, attr)
                except Exception:
                    pass

async def setup(bot: commands.Bot):
    try:
        await bot.add_cog(XPAwardDirectMethodShim(bot))
    except discord.ClientException as e:
        # Ignore duplicate 'already loaded' during reloads
        if "already loaded" not in str(e):
            raise