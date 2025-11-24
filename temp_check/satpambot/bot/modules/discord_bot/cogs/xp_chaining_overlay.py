
import os, time, json, asyncio, logging
from typing import Optional
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

def _int_env(name: str, default: int) -> int:
  try: return int(os.getenv(name, str(default)))
  except Exception: return default

class XPChainingOverlay(commands.Cog):
  """Chain MAGANG -> KERJA with single notify to owner and optional Upstash state."""
  def __init__(self, bot: commands.Bot):
    self.bot = bot
    self.enable = os.getenv("XP_CHAIN_ENABLE","0") == "1"
    self.period_sec = _int_env("XP_CHAIN_PERIOD_SEC", 120)
    self._last_local_notify = 0
    try:
      import aiohttp
      self._aiohttp = aiohttp
    except Exception:
      self._aiohttp = None

  @commands.Cog.listener()
  async def on_ready(self):
    if not self.enable: 
      return
    self.loop_task.change_interval(seconds=self.period_sec)
    self.loop_task.start()

  @tasks.loop(seconds=300)
  async def loop_task(self):
    try:
      await self._tick_once()
    except Exception as e:
      log.error("XPChain tick error: %r", e)

  async def _tick_once(self):
    magang_done = await self._kv_get_bool(os.getenv("XP_MAGANG_DONE_KEY","leina:xp:magang:done"))
    phase_key = os.getenv("XP_PHASE_KEY","leina:xp:phase")
    phase = await self._kv_get_str(phase_key) or "MAGANG"
    if not magang_done or phase != "MAGANG":
      return
    await self._kv_set(phase_key, "KERJA")
    await self._notify_owner_once("Leina masuk fase KERJA. Mohon buka GATE STATUS untuk belajar + bekerja (tanpa spam).")

  async def _notify_owner_once(self, text: str):
    now_ms = int(time.time()*1000)
    notify_key = os.getenv("XP_NOTIFY_KEY","leina:xp:last_notify_ms")
    last_ms_str = await self._kv_get_str(notify_key)
    # Safe parse: allow None/bytes/quoted string -> int; fallback 0
    _cand = "0" if last_ms_str is None else (
        last_ms_str.decode("utf-8", "ignore") if isinstance(last_ms_str, (bytes, bytearray)) else str(last_ms_str)
    )
    _cand = _cand.strip().strip('"').strip("'")
    last_ms = int(_cand) if _cand.isdigit() else 0
    if now_ms - last_ms < 3600*1000:
      return
    owner_id = os.getenv("OWNER_USER_ID","").strip()
    chan_id = os.getenv("OWNER_NOTIFY_CHANNEL_ID","").strip()
    sent = False
    try:
      if owner_id:
        user = self.bot.get_user(int(owner_id))
        if user:
          await user.send(text); sent = True
    except Exception as e:
      log.warning("notify owner DM failed: %r", e)
    if (not sent) and chan_id:
      try:
        ch = self.bot.get_channel(int(chan_id))
        if ch: 
          await ch.send(text); sent = True
      except Exception as e:
        log.warning("notify owner channel failed: %r", e)
    if sent:
      await self._kv_set(notify_key, str(now_ms))

  async def _kv_get_bool(self, key: str) -> bool:
    v = await self._kv_get_str(key)
    return str(v).strip() == "1"

  async def _kv_get_str(self, key: str) -> Optional[str]:
    url = os.getenv("UPSTASH_REDIS_REST_URL","").strip()
    tok = os.getenv("UPSTASH_REDIS_REST_TOKEN","").strip()
    if not url or not tok or not self._aiohttp:
      return getattr(self.bot, "_memkv", {}).get(key)
    try:
      async with self._aiohttp.ClientSession() as s:
        async with s.get(f"{url}/get/{key}", headers={"Authorization": f"Bearer {tok}"}) as r:
          if r.status != 200: return None
          js = await r.json()
          return js.get("result")
    except Exception:
      return None

  async def _kv_set(self, key: str, value: str):
    url = os.getenv("UPSTASH_REDIS_REST_URL","").strip()
    tok = os.getenv("UPSTASH_REDIS_REST_TOKEN","").strip()
    if not url or not tok or not self._aiohttp:
      if not hasattr(self.bot, "_memkv"): self.bot._memkv = {}
      self.bot._memkv[key] = value
      return True
    try:
      async with self._aiohttp.ClientSession() as s:
        async with s.get(f"{url}/set/{key}/{value}", headers={"Authorization": f"Bearer {tok}"}) as r:
          return r.status == 200
    except Exception:
      return False

  @commands.command(name="xp_status", help="Lihat status phase sekarang")
  async def xp_status(self, ctx: commands.Context):
    phase = await self._kv_get_str(os.getenv("XP_PHASE_KEY","leina:xp:phase")) or "MAGANG"
    done = await self._kv_get_bool(os.getenv("XP_MAGANG_DONE_KEY","leina:xp:magang:done"))
    await ctx.send(f"Phase={phase}, MAGANG_DONE={int(done)}")

  @commands.command(name="xp_force_chain", help="Paksa transition ke KERJA (dev/test)")
  async def xp_force_chain(self, ctx: commands.Context):
    await self._kv_set(os.getenv("XP_MAGANG_DONE_KEY","leina:xp:magang:done"), "1")
    await self._kv_set(os.getenv("XP_PHASE_KEY","leina:xp:phase"), "MAGANG")
    await self._tick_once()
    try: await ctx.message.add_reaction("✅")
    except Exception: pass

async def setup(bot: commands.Bot):
  await bot.add_cog(XPChainingOverlay(bot))
