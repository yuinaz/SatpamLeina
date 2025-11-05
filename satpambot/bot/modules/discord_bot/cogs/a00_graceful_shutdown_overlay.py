from __future__ import annotations
import asyncio, signal, logging
from discord.ext import commands
log = logging.getLogger(__name__)
class GracefulShutdownOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._armed = False
        self._install()
    def _install(self):
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except Exception:
            pass
        # SIGINT (Ctrl+C) always available; SIGTERM not on Windows
        def _handle_sig(signame):
            log.warning("[shutdown] got %s -> closing bot gracefully...", signame)
            try:
                asyncio.create_task(self.bot.close())
            except Exception:
                # last resort: stop loop
                try:
                    loop = asyncio.get_event_loop()
                    loop.stop()
                except Exception:
                    pass
        for sig in ("SIGINT","SIGTERM"):
            if hasattr(signal, sig):
                try:
                    signal.signal(getattr(signal, sig), lambda *_: _handle_sig(sig))
                    self._armed = True
                except Exception:
                    pass
        if self._armed:
            log.info("[shutdown] signal handlers armed (Ctrl+C/SIGTERM)")
async def setup(bot: commands.Bot):
    await bot.add_cog(GracefulShutdownOverlay(bot))
