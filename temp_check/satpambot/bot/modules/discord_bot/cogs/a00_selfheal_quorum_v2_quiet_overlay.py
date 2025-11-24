
from discord.ext import commands
import logging

LOG = logging.getLogger(__name__)

class SelfHealQuorumV2Quiet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            import importlib
            m = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.a00_selfheal_quorum_v2_overlay")
            setattr(m, "QUIET_NO_TARGET", True)
            LOG.info("[quorum-v2-quiet] installed (no-target warnings silenced)")
        except Exception as e:
            LOG.debug("[quorum-v2-quiet] not installed: %r", e)
async def setup(bot):
    await bot.add_cog(SelfHealQuorumV2Quiet(bot))