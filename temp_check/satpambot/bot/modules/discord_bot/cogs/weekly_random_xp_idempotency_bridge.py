
try:
    import discord
    from discord.ext import commands
except Exception:  # allow smoke without discord installed
    class discord:  # type: ignore
        class Message: ...
    class commands:  # type: ignore
        class Cog:
            @staticmethod
            def listener(*args, **kwargs):
                def _wrap(fn): return fn
                return _wrap
        @staticmethod
        def listener(*args, **kwargs):
            def _wrap(fn): return fn
            return _wrap

from .....config.auto_defaults import cfg_str
import datetime as dt, asyncio, logging
log = logging.getLogger(__name__)

try:
    from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
except Exception:
    UpstashClient = None

def _week_id(d: dt.datetime) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{int(w):02d}"

class WeeklyRandomXPIdempotencyBridge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ns = cfg_str("WEEKLY_XP_IDEMPOTENT_NS", "weekly_xp:done_week") or "weekly_xp:done_week"
        self.title_prefix = cfg_str("WEEKLY_XP_TITLE_PREFIX", "Weekly Random XP") or "Weekly Random XP"
        self.client = UpstashClient() if UpstashClient else None
        self._task = None

    @commands.Cog.listener()
    async def on_ready(self):
        if self._task: return
        self._task = asyncio.create_task(self._sync_state())

    async def _sync_state(self):
        await asyncio.sleep(5)
        if not self.client or not getattr(self.client, "enabled", False): return
        now = dt.datetime.now(dt.timezone.utc)
        wk = _week_id(now)
        try:
            v = await self.client.get_json(self.ns)
            if isinstance(v, dict) and v.get("week") == wk:
                from pathlib import Path
                root = Path(__file__).resolve().parents[5]
                state = root / "data" / "neuro-lite" / "weekly_event_state.json"
                state.parent.mkdir(parents=True, exist_ok=True)
                state.write_text('{"done_week":"%s"}' % wk, encoding="utf-8")
                log.info("[weekly-idem] synced local state=%s", wk)
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_message(self, m):
        try:
            if not getattr(getattr(m,"author",None),"bot",False): return
            if not getattr(m,"embeds",None): return
            if len(m.embeds) == 0: return
            e = m.embeds[0]
            title = (getattr(e,"title","") or "")
            if not title.startswith(self.title_prefix): return
            if not self.client or not getattr(self.client, "enabled", False): return
            now = dt.datetime.now(dt.timezone.utc)
            wk = _week_id(now)
            await self.client.set_json(self.ns, {"week": wk, "msg_id": int(m.id)}, ttl=60*60*24*70)
            log.info("[weekly-idem] week marked %s", wk)
        except Exception:
            pass

async def setup(bot): await bot.add_cog(WeeklyRandomXPIdempotencyBridge(bot))