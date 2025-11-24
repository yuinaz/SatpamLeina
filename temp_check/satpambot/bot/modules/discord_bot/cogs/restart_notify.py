from __future__ import annotations

from discord.ext import commands

# SPDX-License-Identifier: MIT
# Posts a "Restart complete" embed ONLY if a sentinel from a command-triggered restart is present.

import os
import asyncio
import datetime as dt
from typing import Optional

import discord

try:
    from satpambot.bot.modules.discord_bot.helpers.restart_sentinel import pop as pop_restart  # type: ignore
except Exception:
    from .helpers.restart_sentinel import pop as pop_restart  # type: ignore

LOG_NAMES = [
    "log-botphising",
    "log-botphishing",
    "log-satpam",
    "banlog",
    "errorlog-bot",
    "mod-log",
]

def _parse_int_env(*keys: str) -> Optional[int]:
    for k in keys:
        v = os.getenv(k)
        if v:
            try:
                return int(v)
            except Exception:
                pass
    return None

class RestartNotify(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._sent_once = False

    async def _find_log_channel(self) -> Optional[discord.abc.Messageable]:
        cid = _parse_int_env("LOG_CHANNEL_ID", "LOG_CHANNEL_ID_RAW", "LOG_CHANNEL_ID_INT")
        if cid:
            ch = self.bot.get_channel(cid)
            if ch and isinstance(ch, (discord.TextChannel, discord.Thread, discord.VoiceChannel, discord.StageChannel)):
                return ch
        for g in self.bot.guilds:
            for name in LOG_NAMES:
                ch = discord.utils.get(g.text_channels, name=name)  # type: ignore
                if ch:
                    return ch
        for g in self.bot.guilds:
            if g.system_channel:
                return g.system_channel
        return None

    @commands.Cog.listener()
    async def on_ready(self):
        if self._sent_once:
            return
        self._sent_once = True

        # Allow app command registration to settle
        await asyncio.sleep(1.0)

        data = pop_restart()
        if not data:
            return  # No command-triggered restart

        ch = await self._find_log_channel()
        if not ch:
            return

        wib = dt.timezone(dt.timedelta(hours=7), name="WIB")
        now = dt.datetime.now(dt.timezone.utc)
        ts_wib = dt.datetime.now(wib).strftime("%Y-%m-%d %H:%M WIB")

        title = "✅ Restart complete"
        desc = "Bot kembali online dan stabil."
        actor = data.get("actor_id")
        if actor:
            try:
                user = await self.bot.fetch_user(int(actor))
                if user:
                    desc += f" (oleh {user.mention})"
            except Exception:
                pass

        emb = discord.Embed(title=title, description=desc, colour=discord.Colour.green(), timestamp=now)
        emb.set_footer(text=f"SatpamBot • {ts_wib}")
        try:
            await ch.send(embed=emb)
        except Exception:
            pass
async def setup(bot: commands.Bot):
    await bot.add_cog(RestartNotify(bot))