from discord.ext import commands
from discord.ext import tasks

import os, json, time, logging
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

async def _upstash_set(url, token, key, value):
    if not (url and token): return False
    try:
        import aiohttp
        async with aiohttp.ClientSession() as sess:
            r = await sess.post(f"{url}/set/{key}/{value}", headers={"Authorization": f"Bearer {token}"}, timeout=10)
            return r.status == 200
    except Exception as e:
        log.debug("[xp-checkpoint] upstash set failed: %r", e)
        return False

class XPCheckpointDiscordBackend(commands.Cog):
    """
    Menyimpan snapshot XP (best-effort) ke Upstash menggunakan REST.
    Tidak mengubah format store lain; hanya menulis key tunggal bila ENV tersedia.
    """
    def __init__(self, bot):
        self.bot = bot
        self.key = os.getenv("XP_CHECKPOINT_KEY", "xp:bot:checkpoint")
        self.url = (os.getenv("UPSTASH_REDIS_REST_URL","") or "").rstrip("/") or None
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN") or None
        self.period = max(60, int(os.getenv("XP_CHECKPOINT_PERIOD_SEC","600") or "600"))
        self._task = self._tick.start()

    def cog_unload(self):
        try: self._task.cancel()
        except Exception: pass

    def _snapshot(self):
        # Best-effort: minta state dari bot jika tersedia
        snap = {"ts": int(time.time())}
        for name in ("export_xp_state", "dump_xp_state", "get_xp_state"):
            fn = getattr(self.bot, name, None)
            if callable(fn):
                try:
                    data = fn()
                    if isinstance(data, dict):
                        snap.update(data)
                        break
                except Exception:
                    pass
        return snap

    @tasks.loop(seconds=30)
    async def _tick(self):
        now = int(time.time())
        if now % self.period != 0:
            return
        if not (self.url and self.token):
            return
        try:
            data = json.dumps(self._snapshot(), ensure_ascii=False)
            await _upstash_set(self.url, self.token, self.key, data)
        except Exception as e:
            log.debug("[xp-checkpoint] tick failed: %r", e)

    @_tick.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(XPCheckpointDiscordBackend(bot))