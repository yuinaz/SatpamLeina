from discord.ext import commands
import os
import logging

log = logging.getLogger(__name__)

TARGET_NAMES = [
    "log-botphising",
    "log-botphishing",
    "log_botphising",
    "log_botphishing",
    "log-phish", "log_phish"
]

class PublicGateChannelOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # If PUBLIC_REPORT_CHANNEL_ID is already set, do nothing.
        if os.getenv("PUBLIC_REPORT_CHANNEL_ID"):
            log.info("[public_gate_overlay] Using PUBLIC_REPORT_CHANNEL_ID=%s", os.getenv("PUBLIC_REPORT_CHANNEL_ID"))
            return
        # Search by name across guilds
        for g in self.bot.guilds:
            try:
                for ch in g.text_channels:
                    nm = (ch.name or "").lower()
                    if any(key in nm for key in TARGET_NAMES):
                        os.environ["PUBLIC_REPORT_CHANNEL_ID"] = str(ch.id)
                        log.info("[public_gate_overlay] PUBLIC_REPORT_CHANNEL_ID set to #%s (%s)", ch.name, ch.id)
                        return
            except Exception:
                continue
        log.warning("[public_gate_overlay] No matching channel by name; set PUBLIC_REPORT_CHANNEL_ID/LOG_CHANNEL_ID manually.")
async def setup(bot):
    await bot.add_cog(PublicGateChannelOverlay(bot))