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

class PublicGateForceBind(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Pick target channel id
        chan_id = os.getenv("PUBLIC_REPORT_CHANNEL_ID")
        if not chan_id:
            for g in self.bot.guilds:
                for ch in getattr(g, "text_channels", []):
                    nm = (getattr(ch, "name", "") or "").lower()
                    if any(key == nm for key in TARGET_NAMES):
                        chan_id = str(ch.id)
                        os.environ["PUBLIC_REPORT_CHANNEL_ID"] = chan_id
                        log.info("[public_gate_force] Found #%s → id=%s", ch.name, chan_id)
                        break
                if chan_id:
                    break

        if not chan_id:
            log.warning("[public_gate_force] No report channel found; set PUBLIC_REPORT_CHANNEL_ID manually.")
            return

        # Bind to PublicChatGate cog if present
        for name, cog in self.bot.cogs.items():
            # match by class name without import
            if getattr(cog, "__class__", None) and cog.__class__.__name__.lower().startswith("publicchatgate"):
                try:
                    setattr(cog, "_report_channel_id", int(chan_id))
                    log.info("[public_gate_force] Bound PublicChatGate._report_channel_id → %s", chan_id)
                except Exception as e:
                    log.warning("[public_gate_force] Failed to bind: %r", e)
                break
async def setup(bot):
    await bot.add_cog(PublicGateForceBind(bot))