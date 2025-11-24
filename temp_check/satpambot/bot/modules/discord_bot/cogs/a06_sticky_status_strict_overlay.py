from discord.ext import commands
import inspect, logging, asyncio

log = logging.getLogger(__name__)

async def _maybe_add_cog(bot, cog):
    add = getattr(bot, "add_cog", None)
    if not add:
        return
    try:
        res = add(cog)
        if inspect.isawaitable(res):
            await res
    except Exception as e:
        log.exception("failed to add cog %s: %s", type(cog).__name__, e)

import json, logging

log = logging.getLogger(__name__)

def _load_local_json():
    for cand in ("local.json", "/opt/render/project/src/local.json"):
        try:
            with open(cand, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

class _StickyStatusStrict(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        cfg = _load_local_json().get("overlays", {})
        self.titles = cfg.get("strict_sticky_titles", ["Periodic Status", "Maintenance", "Heartbeat"])
        log.info("[sticky_status.strict] active; titles=%s", self.titles)
async def setup(bot):
    if bot.get_cog("_StickyStatusStrict"):
        return
    await _maybe_add_cog(bot, _StickyStatusStrict(bot))