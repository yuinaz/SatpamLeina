from discord.ext import commands

import os
import logging

log = logging.getLogger(__name__)

class ForceSeniorProgressOverlay(commands.Cog):
    """Prefer 'senior' curriculum & progress, regardless of default guards."""
    def __init__(self, bot):
        self.bot = bot
        os.environ.setdefault("CURRICULUM_PREFERRED_TRACK", "senior")
        log.info("[senior-overlay] CURRICULUM_PREFERRED_TRACK=senior")

        # Best-effort patches for modules that keep module-level flags
        try:
            import satpambot.bot.modules.discord_bot.cogs.neuro_curriculum_bridge as bridge
            if hasattr(bridge, "CURRICULUM_SPLIT"):
                bridge.CURRICULUM_SPLIT = {"junior": 0, "senior": 1}
                log.info("[senior-overlay] curriculum split forced to %s", bridge.CURRICULUM_SPLIT)
        except Exception as e:
            log.warning("[senior-overlay] split patch skipped: %r", e)

        try:
            import satpambot.bot.modules.discord_bot.cogs.learning_progress_reporter as reporter
            if hasattr(reporter, "PREFERRED_TRACK"):
                reporter.PREFERRED_TRACK = "senior"
                log.info("[senior-overlay] reporter preferred track=senior")
        except Exception as e:
            log.warning("[senior-overlay] reporter patch skipped: %r", e)

async def setup(bot):
    await bot.add_cog(ForceSeniorProgressOverlay(bot))