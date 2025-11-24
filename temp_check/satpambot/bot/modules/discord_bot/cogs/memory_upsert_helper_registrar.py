from __future__ import annotations

from discord.ext import commands

"""
Register a default memory_upsert helper so miners don't warn when helper is missing.
Safe, idempotent, and does not change existing config/main.
"""
import logging

log = logging.getLogger("satpambot.memory_upsert_helper_registrar")

try:
    # Import the helper that other cogs expect
    from satpambot.bot.modules.discord_bot.helpers.memory_upsert import upsert_pinned_memory
except Exception as e:
    upsert_pinned_memory = None  # will log on setup
    log.warning("[memory-upsert-registrar] helper import failed: %r", e)

class MemoryUpsertHelperRegistrar(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Bind attribute only if not already provided by the runtime
        if getattr(bot, "memory_upsert_helper", None) is None:
            if upsert_pinned_memory is not None:
                bot.memory_upsert_helper = upsert_pinned_memory
                log.info("[memory-upsert-registrar] helper registered (bot.memory_upsert_helper)")
            else:
                log.warning("[memory-upsert-registrar] helper missing; miner will no-op pin updates but continue")
async def setup(bot: commands.Bot):
    await bot.add_cog(MemoryUpsertHelperRegistrar(bot))