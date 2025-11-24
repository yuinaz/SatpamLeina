from __future__ import annotations
import os, logging
from collections import defaultdict
from datetime import date
import discord
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

def _parse_ids(s: str) -> set[int]:
    out:set[int] = set()
    for part in (s or "").replace(";",",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except Exception:
            pass
    return out

class LearningPassiveObserver(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.per_msg = int(os.getenv("LEARNING_PASSIVE_XP_PER_MESSAGE", "15") or "15")
        self.daily_cap = int(os.getenv("LEARNING_PASSIVE_DAILY_CAP", "0") or "0")
        self.allow_guilds = _parse_ids(os.getenv("LEARNING_PASSIVE_ALLOW_GUILDS",""))
        self.deny_channels = _parse_ids(os.getenv("LEARNING_PASSIVE_DENY_CHANNELS",""))
        self.today = date.today()
        self.used_today: dict[int,int] = defaultdict(int) if self.daily_cap > 0 else {}
        self._ticker.start()
        log.info("[passive-xp] per_msg=%s daily_cap=%s (<=0 means unlimited)", self.per_msg, self.daily_cap)

    def cog_unload(self):
        try: self._ticker.cancel()
        except Exception: pass

    @tasks.loop(minutes=5.0)
    async def _ticker(self):
        if self.daily_cap > 0 and date.today() != self.today:
            self.today = date.today()
            self.used_today.clear()

    def _allowed(self, m: discord.Message) -> bool:
        if m.author.bot: return False
        if self.per_msg <= 0: return False
        if self.deny_channels and m.channel.id in self.deny_channels: return False
        if self.allow_guilds and m.guild and (m.guild.id not in self.allow_guilds): return False
        return True

    def _grant_amount(self, uid: int) -> int:
        if self.daily_cap <= 0: return self.per_msg
        used = self.used_today.get(uid, 0)
        if used >= self.daily_cap: return 0
        remain = self.daily_cap - used
        return self.per_msg if self.per_msg <= remain else remain

    def _after_grant(self, uid: int, delta: int):
        if self.daily_cap > 0 and delta > 0:
            self.used_today[uid] = self.used_today.get(uid, 0) + delta

    @commands.Cog.listener("on_message")
    async def _on_message(self, m: discord.Message):
        if not self._allowed(m): return
        uid = m.author.id
        delta = self._grant_amount(uid)
        if delta <= 0: return
        reason = "passive_message"
        # Dispatch with positional signature (uid, amount, reason) for broad compatibility
        try: self.bot.dispatch("xp_add", uid, delta, reason)
        except Exception: pass
        try: self.bot.dispatch("satpam_xp", uid, delta, reason)
        except Exception: pass
        try: self.bot.dispatch("xp_award", uid, delta, reason)
        except Exception: pass
        self._after_grant(uid, delta)

async def setup(bot: commands.Bot):
    await bot.add_cog(LearningPassiveObserver(bot))
