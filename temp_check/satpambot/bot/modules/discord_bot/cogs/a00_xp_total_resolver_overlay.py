import logging, json, inspect, asyncio, os
from discord.ext import commands
from satpambot.bot.modules.discord_bot.helpers import xp_total_resolver as _base_res
from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV

log = logging.getLogger(__name__)

class XPTotalResolverOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.kv = PinnedJSONKV(bot)
        # patch functions
        base_get = _base_res.resolve_senior_total
        base_get_status = getattr(_base_res, "_get_status_json", None)

        async def resolve_senior_total_dual():
            # 1) Try base (Upstash)
            try:
                v = await base_get()  # type: ignore
                if v is not None:
                    return v
            except Exception:
                pass
            # 2) Fallback to Discord KV
            try:
                key = os.getenv("XP_SENIOR_KEY", "xp:bot:senior_total")
                m = await self.kv.get_map()
                if key in m:
                    return int(m[key])
            except Exception as e:
                log.warning("[xp-resolver-overlay] fallback senior_total failed: %r", e)
            return None

        async def _get_status_json_dual():
            # 1) Try base
            if callable(base_get_status):
                try:
                    sj = await base_get_status()  # type: ignore
                    if sj:
                        return sj
                except Exception:
                    pass
            # 2) Fallback to Discord KV
            try:
                m = await self.kv.get_map()
                sj = m.get("learning:status_json")
                if isinstance(sj, dict):
                    return sj
                if isinstance(sj, str):
                    return json.loads(sj)
            except Exception as e:
                log.warning("[xp-resolver-overlay] fallback status_json failed: %r", e)
            return None

        # monkey patch
        _base_res.resolve_senior_total = resolve_senior_total_dual  # type: ignore
        if callable(base_get_status):
            _base_res._get_status_json = _get_status_json_dual  # type: ignore

async def setup(bot: commands.Bot):
    await bot.add_cog(XPTotalResolverOverlay(bot))
