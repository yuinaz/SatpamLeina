from __future__ import annotations

from discord.ext import commands
import logging, importlib

log = logging.getLogger(__name__)
MODULES = [
    # Previously delivered base overlays (if present in repo):
    "satpambot.bot.modules.discord_bot.cogs.a00_auto_local_sync",
    "satpambot.bot.modules.discord_bot.cogs.a29_public_mode_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a28_disable_talking_unblock",
    "satpambot.bot.modules.discord_bot.cogs.a02_dm_muzzle_cfg_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a25_governor_cfg_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a02_dm_muzzle_mode_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a24_progress_explicit_thread_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a24_qna_channel_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a03_owner_notify_redirect_thread",
    "satpambot.bot.modules.discord_bot.cogs.admin_slash_control",
    "satpambot.bot.modules.discord_bot.cogs.admin_interview_gate",
    "satpambot.bot.modules.discord_bot.cogs.a31_public_mode_interview_gate",
    # New Plus:
    "satpambot.bot.modules.discord_bot.cogs.a26_neuro_governor_policy_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a26_shadow_cadence_tuner",
    "satpambot.bot.modules.discord_bot.cogs.a26_text_miner_tuning_overlay",
    "satpambot.bot.modules.discord_bot.cogs.web_search_groq_bridge",
    "satpambot.bot.modules.discord_bot.cogs.selfheal_coordinator_fix",
    "satpambot.bot.modules.discord_bot.cogs.a03_alert_prefix_severity_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a27_rate_limit_policy_overlay",
]

class OverlayAutoloadPlus(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        for mod in MODULES:
            try:
                m = importlib.import_module(mod)
                setup = getattr(m, "setup", None)
                if callable(setup):
                    await self.bot.load_extension(mod)
                    log.info("[autoload_plus] loaded extension %s", mod)
                else:
                    log.info("[autoload_plus] imported overlay %s", mod)
            except Exception as e:
                log.warning("[autoload_plus] skip %s: %s", mod, e)
async def setup(bot: commands.Bot):
    await bot.add_cog(OverlayAutoloadPlus(bot))