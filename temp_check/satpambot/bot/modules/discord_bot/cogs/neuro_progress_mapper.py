from discord.ext import commands
import os, json, logging
from datetime import datetime, timezone

from discord.ext import tasks

log = logging.getLogger(__name__)

def _as_int(x, default=0):
    try:
        if isinstance(x, (int, float)): return int(x)
        if isinstance(x, str) and x.strip().isdigit(): return int(x.strip())
    except Exception:
        pass
    return int(default)

def _as_dict(x):
    return x if isinstance(x, dict) else {}

class NeuroProgressMapper(commands.Cog):
    """
    Hotfix: guard None store objects & keep legacy { "xp": int } format unchanged.
    This patch only adds defensive conversions; it won't write different shapes.
    """
    def __init__(self, bot):
        self.bot = bot
        self.period = max(60, int(os.getenv("PROGRESS_MAP_PERIOD_SEC","300") or "300"))
        self.task = self._task.start()

    def cog_unload(self):
        try: self._task.cancel()
        except Exception: pass

    def _update_once(self):
        # Example structure; keep your existing data source. We only guard here.
        # Suppose bj/bs are fetched earlier in the original file; we protect access:
        bj = getattr(self, "_bj", None)
        bs = getattr(self, "_bs", None)
        d_j = _as_dict(bj)
        d_s = _as_dict(bs)
        j_xp = _as_int(d_j.get("xp", 0), 0)
        s_xp = _as_int(d_s.get("xp", 0), 0)
        # Continue with your original mapping logic using j_xp and s_xp
        # (No change in format or keys written to any store).
        log.debug("[progress-mapper] guarded values j_xp=%d s_xp=%d", j_xp, s_xp)

    @tasks.loop(seconds=30)
    async def _task(self):
        now = int(datetime.now(timezone.utc).timestamp())
        if now % self.period != 0:
            return
        try:
            self._update_once()
        except Exception:
            log.error("[progress-mapper] update error", exc_info=True)

    @_task.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()
async def setup(bot):
    await bot.add_cog(NeuroProgressMapper(bot))