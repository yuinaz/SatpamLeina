from discord.ext import commands
import asyncio
import logging
import os
import time
from collections import Counter
from typing import Optional

try:
    import discord  # noqa: F401
    from discord.ext import tasks
except Exception:
    # keep import-light for smoke checks; this file is a "soft" addon
    discord = None
    commands = None
    tasks = None

"""
A tiny noise-tamer for delete_safe_shim_plus logger.

- Does NOT touch any delete protection logic.
- Only coalesces repetitive INFO logs like:
    "[delete_safe_plus] ignore delete for pre-session log message (session-scope)"
    "[delete_safe_plus] ignore delete for pinned in #log-botphising"
- Controlled via ENV:
    DELETE_SAFE_LOG_MODE=summary|verbose   (default: summary)
    DELETE_SAFE_SUMMARY_SECS=30            (flush interval)
"""

TARGET_LOGGER_NAME = "satpambot.bot.modules.discord_bot.cogs.delete_safe_shim_plus"
SUMMARY_LOGGER_NAME = TARGET_LOGGER_NAME + ".summary"

COALESCE_DEFAULT = os.getenv("DELETE_SAFE_LOG_MODE", "summary").lower() != "verbose"
SUMMARY_EVERY = int(os.getenv("DELETE_SAFE_SUMMARY_SECS", "30"))

class _CoalesceFilter(logging.Filter):
    def __init__(self, target: str, coalesce: bool = True) -> None:
        super().__init__(name=target)
        self.coalesce = coalesce
        self._hits = Counter()
        self._patterns = (
            "ignore delete for pre-session",
            "ignore delete for pinned",
            "ignored delete: pre-session",
            "ignored delete: pinned",
        )
        self._lock = asyncio.Lock()

    def _match(self, msg: str) -> Optional[str]:
        m = msg.lower()
        for p in self._patterns:
            if p in m:
                return p
        return None

    def filter(self, record: logging.LogRecord) -> bool:
        if not self.coalesce:
            return True
        try:
            msg = record.getMessage()  # formatting-safe
        except Exception:
            return True
        # only tame the intended noise
        key = self._match(msg)
        if key is None or record.levelno > logging.INFO:
            return True
        # Drop this record, and count it for summary.
        # NOTE: filter is sync; keep counters lightweight
        self._hits[key] += 1
        return False  # swallow

    async def flush_summary(self) -> None:
        if not self.coalesce:
            return
        async with self._lock:
            if not self._hits:
                return
            logger = logging.getLogger(SUMMARY_LOGGER_NAME)
            # Emit one line per pattern
            for key, n in list(self._hits.items()):
                logger.info("[delete_safe_plus] %s ×%d (coalesced)", key, n)
            self._hits.clear()

class DeleteSafeNoiseCoalesce(commands.Cog if commands else object):
    """Discord cog that installs a Filter and flushes summaries on an interval."""
    def __init__(self, bot=None):
        self.bot = bot
        self.coalesce = COALESCE_DEFAULT
        self.filter = _CoalesceFilter(TARGET_LOGGER_NAME, self.coalesce)
        self._installed = False
        self._target_logger = logging.getLogger(TARGET_LOGGER_NAME)
        if self.coalesce:
            self._install()
        # background task for periodic summary
        if tasks:
            self._task = self._summary_task.start()
        else:
            self._task = None

    def _install(self):
        if self._installed:
            return
        # Install only on the target logger (not root)
        self._target_logger.addFilter(self.filter)
        self._installed = True
        logging.getLogger(__name__).info(
            "[delete_safe_noise_coalesce] installed (mode=%s, every=%ss)",
            "summary" if self.coalesce else "verbose", SUMMARY_EVERY
        )

    def cog_unload(self):
        # detach filter and stop task
        try:
            self._target_logger.removeFilter(self.filter)
        except Exception:
            pass
        if tasks and getattr(self, "_task", None):
            try:
                self._task.cancel()
            except Exception:
                pass

    if tasks:
        @tasks.loop(seconds=max(5, SUMMARY_EVERY))
        async def _summary_task(self):
            await self.filter.flush_summary()

        @_summary_task.before_loop
        async def _before(self):
            if self.bot and hasattr(self.bot, "wait_until_ready"):
                await self.bot.wait_until_ready()
async def setup(bot):
    # New-style extension loader
    cog = DeleteSafeNoiseCoalesce(bot)
    if getattr(bot, "add_cog", None):
        await bot.add_cog(cog)

# Old-style for backward compatibility (discord.py <2.0)