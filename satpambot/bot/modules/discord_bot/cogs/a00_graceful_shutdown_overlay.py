from __future__ import annotations
import asyncio, logging, os, signal, sys
from discord.ext import commands
log = logging.getLogger(__name__)
HARD_KILL_SEC = int(os.getenv("SHUTDOWN_HARD_KILL_SEC","6") or "6")
class GracefulShutdownOverlay(commands.Cog):
    def __init__(self, bot): self.bot=bot; self._arm()
    def _arm(self):
        def handle(sig): 
            log.info("[shutdown] starting graceful shutdown (%s) ...", sig)
            asyncio.create_task(self._shutdown())
        for s in ("SIGINT","SIGTERM"):
            if hasattr(signal, s):
                try: signal.signal(getattr(signal,s), lambda *_: handle(s))
                except Exception: pass
        log.info("[shutdown] signal handlers armed")
    async def _shutdown(self):
        try: await asyncio.wait_for(self.bot.close(), timeout=HARD_KILL_SEC)
        except Exception as e: log.warning("[shutdown] bot.close err: %s", e)
        try: asyncio.get_event_loop().stop()
        except Exception: pass
        try: os._exit(0)
        except Exception: sys.exit(0)
async def setup(bot): await bot.add_cog(GracefulShutdownOverlay(bot))
