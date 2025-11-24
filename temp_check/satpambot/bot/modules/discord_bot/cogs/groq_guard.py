from __future__ import annotations

from discord.ext import commands

"""
Groq guard:
- If GROQ API key is missing/empty, disable Groq-dependent cogs to avoid 403 spam.
- Non-invasive: does not modify existing files; can run on both local and Render.
"""
import os
import logging

log = logging.getLogger("satpambot.groq_guard")

GROQ_COG_NAMES = (
    # Try common names present in this project
    "SelfHealGroqAgent",
    "SelfHealRuntime",
)

def _has_valid_groq_key() -> bool:
    key = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_KEY") or os.getenv("GROQ_TOKEN")
    if not key:
        return False
    # very light sanity check
    return len(key.strip()) >= 20

class GroqGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        if not _has_valid_groq_key():
            # Disable noisy Groq cogs proactively
            for name in GROQ_COG_NAMES:
                cog = self.bot.get_cog(name)
                if cog is None:
                    continue
                try:
                    # If the cog exposes a graceful shutdown, use it
                    shutdown = getattr(cog, "shutdown", None)
                    if shutdown:
                        if callable(shutdown):
                            res = shutdown()
                            if hasattr(res, "__await__"):
                                await res  # if coroutine
                except Exception as e:
                    log.debug("[groq-guard] %s shutdown call failed: %r", name, e)
                try:
                    self.bot.remove_cog(name)
                    log.info("[groq-guard] disabled %s (no GROQ key) — preventing httpx 403 spam", name)
                except Exception as e:
                    log.debug("[groq-guard] remove_cog %s failed: %r", name, e)
async def setup(bot: commands.Bot):
    await bot.add_cog(GroqGuard(bot))