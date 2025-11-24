from __future__ import annotations

from discord.ext import commands

import logging, asyncio
import discord

from satpambot.config.runtime import cfg

log = logging.getLogger(__name__)

class UpgradeAdvisor(commands.Cog):
    """Diet-DM: tidak mengirim 'Proposal: enable_cog …'. Hanya membiarkan sistem lain kirim Startup/Periodic."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # respect flags, but default is diet
        self.proposal_dm = bool(cfg('AUTO_UPDATE_PROPOSAL_DM', False))
        self.critical_only = bool(cfg('AUTO_UPDATE_CRITICAL_ONLY', True))

    async def cog_load(self):
        # Tidak mengirim proposal apa pun saat boot
        log.info("[upgrade_advisor] diet mode active (proposal_dm=%s, critical_only=%s)",
                 self.proposal_dm, self.critical_only)

    # Compatibility stubs if other modules import callsites
    async def send_startup_report(self):
        # Biarkan auto_update_manager atau restart_notifier_boot yang kirim laporan startup
        return
async def setup(bot: commands.Bot):
    await bot.add_cog(UpgradeAdvisor(bot))