from discord.ext import commands
import os, json, logging
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

from ..helpers.upstash_client import UpstashClient
from ..helpers.ladder_loader import load_ladders, compute_senior_label

log = logging.getLogger(__name__)

class PresenceFromUpstash(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.period = max(30, int(os.getenv("LEINA_PRESENCE_PERIOD_SEC","60") or "60"))
        self.template = os.getenv("LEINA_PRESENCE_TEMPLATE","🎓 {label} • {percent:.1f}%")
        self.status_mode = (os.getenv("LEINA_PRESENCE_STATUS") or "online").lower().strip()
        self.client = UpstashClient()
        self.ladders = load_ladders(__file__)
        self._last = None
        if os.getenv("LEINA_PRESENCE_DISABLE"):
            log.info("[presence] disabled via LEINA_PRESENCE_DISABLE")
        else:
            self.task = self.loop.start()

    def cog_unload(self):
        try: self.loop.cancel()
        except Exception: pass

    def _discord_status(self):
        m = self.status_mode
        return {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible
        }.get(m, discord.Status.online)

    @tasks.loop(seconds=30)
    async def loop(self):
        if not self.client.enabled:
            return
        now = datetime.now(timezone.utc)
        if int(now.timestamp()) % self.period != 0:
            return
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                raw = await self.client.get("learning:status_json")
                if raw:
                    try:
                        j = json.loads(raw)
                        label = j.get("label") or "N/A"
                        percent = float(j.get("percent") or 0.0)
                    except Exception:
                        label, percent = "N/A", 0.0
                else:
                    xp_key = os.getenv("XP_SENIOR_KEY","xp:bot:senior_total")
                    total_raw = await self.client.get(xp_key)
                    try: total = int(total_raw or 0)
                    except Exception:
                        try:
                            jt = json.loads(total_raw); total = int(jt.get("overall",0))
                        except Exception: total = 0
                    label, percent, _ = compute_senior_label(total, self.ladders)

                text = self.template.format(label=label, percent=percent)
                if text != self._last:
                    await self.bot.change_presence(
                        status=self._discord_status(),
                        activity=discord.Game(name=text)
                    )
                    self._last = text
        except Exception as e:
            log.debug("[presence] update skipped: %s", e)

    @loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()
async def setup(bot: commands.Bot):
    await bot.add_cog(PresenceFromUpstash(bot))
# LEINA_UPSTASH_SAFE: skip overlay if missing config
import os as _os
if not (_os.getenv('UPSTASH_URL') and _os.getenv('UPSTASH_TOKEN')):
    ENABLE = False
