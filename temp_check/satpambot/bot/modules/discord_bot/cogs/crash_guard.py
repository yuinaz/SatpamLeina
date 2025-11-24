from __future__ import annotations

from discord.ext import commands

import time
import discord
from discord.ext import commands, tasks
from satpambot.config.runtime import cfg
try:
    from .selfheal_router import send_selfheal

except Exception:
    async def send_selfheal(bot, embed):  # fallback: DM owner
        owner = cfg('OWNER_USER_ID')
        if not owner: return
        user = bot.get_user(int(owner)) or await bot.fetch_user(int(owner))
        if user: await user.send(embed=embed)

def _mk_embed(title: str, desc: str, color: int):
    return discord.Embed(title=title, description=desc, color=color)

class CrashGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.window = 600  # 10 minutes
        self.threshold = int(cfg('CRASH_ERR_PER_10M', 12))
        self._errors = []  # list of (ts, where, brief)
        if hasattr(self, 'housekeep'):
            self.housekeep.start()  # type: ignore

    def _prune(self):
        cutoff = time.time() - self.window
        self._errors = [e for e in self._errors if e[0] >= cutoff]

    @tasks.loop(seconds=60)
    async def housekeep(self):
        try:
            self._prune()
            if len(self._errors) >= self.threshold:
                msg = f"High error rate detected (>{self.threshold}/10m). Switching to half-power."
                await send_selfheal(self.bot, _mk_embed('CrashGuard', msg, 0xe74c3c))
                self._errors.clear()
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_error(self, event_method: str, *args, **kwargs):
        self._errors.append((time.time(), event_method, f'Event {event_method} failed'))

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, exception: Exception):
        brief = f'Cmd {getattr(ctx.command, "qualified_name", "?")} error: {type(exception).__name__}'
        self._errors.append((time.time(), 'command', brief))
async def setup(bot):
    await bot.add_cog(CrashGuard(bot))