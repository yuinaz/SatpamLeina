from __future__ import annotations

from discord.ext import commands

"""
Graceful shutdown handler:
- Handles SIGTERM (Render) and Ctrl+C (Windows/Linux) without changing main.py
- Closes Discord bot cleanly and prevents noisy tracebacks as much as possible
"""
import asyncio
import logging
import signal
import sys
import atexit
import os
from typing import Optional

import discord

log = logging.getLogger("satpambot.graceful_shutdown")

class GracefulShutdown(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._shutdown_started = False
        self._install_handlers()

        # best-effort: ensure close at process exit
        atexit.register(self._sync_finalizer)

    def _install_handlers(self):
        loop = asyncio.get_running_loop()
        # SIGTERM is supported on Linux (Render). For Windows, we rely on SIGINT handler.
        try:
            loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(self.shutdown("SIGTERM")))
            log.debug("[shutdown] SIGTERM handler installed")
        except (NotImplementedError, RuntimeError):
            pass

        # Windows: signal.signal works for SIGINT (Ctrl+C)
        try:
            signal.signal(signal.SIGINT, self._sigint_handler)
            log.debug("[shutdown] SIGINT handler installed")
        except Exception:
            pass

    def _sigint_handler(self, signum, frame):
        # Schedule async shutdown on the running loop
        try:
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(lambda: asyncio.create_task(self.shutdown("SIGINT")))
        except RuntimeError:
            # No running loop? do sync finalizer
            self._sync_finalizer()

    async def shutdown(self, reason: str = "unknown"):
        os.environ['LEINA_SHUTTING_DOWN']='1'
        if self._shutdown_started:
            return
        self._shutdown_started = True
        log.info("[shutdown] starting graceful shutdown (%s) ...", reason)
        try:
            await self.bot.change_presence(status=discord.Status.invisible)
        except Exception:
            pass

        # Give running tasks a moment to yield
        await asyncio.sleep(0.05)

        # Close the bot cleanly
        try:
            await self.bot.close()
        except Exception:
            pass

        # After bot.close(), let loop stop soon
        try:
            loop = asyncio.get_running_loop()
            loop.stop()
        except Exception:
            pass

        log.info("[shutdown] done.")

    def _sync_finalizer(self):
        # Called on atexit as a last resort; try closing the bot if still running.
        try:
            if not getattr(self.bot, "is_closed", lambda: True)():
                try:
                    asyncio.run(self.bot.close())
                except Exception:
                    pass
        except Exception:
            pass
async def setup(bot: commands.Bot):
    await bot.add_cog(GracefulShutdown(bot))