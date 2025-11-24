
from __future__ import annotations
import asyncio, inspect, logging
from discord.ext import commands
from satpambot.bot.modules.discord_bot.helpers.channel_policy import allowed_for
from satpambot.bot.modules.discord_bot.helpers.task_tools import create_task_any

log = logging.getLogger(__name__)

KEYWORDS = {
    "qna": ("qna","autolearn","auto_answer","answer_overlay"),
    "xp": ("xp","learn","neuro","passive","observer","miner")
}

def _kind_for_module(modname: str) -> str:
    m = (modname or "").lower()
    for kind, kws in KEYWORDS.items():
        if any(k in m for k in kws):
            return kind
    return ""

def _wrap_on_message(kind: str, fn):
    async def wrapper(*args, **kwargs):
        try:
            message = args[1] if len(args) >= 2 else kwargs.get("message")
            ch_id = int(getattr(getattr(message, "channel", None), "id", 0) or 0)
            if ch_id and not allowed_for(kind or "", ch_id):
                return
        except Exception as e:
            log.debug("[chan-policy] precheck skipped: %r", e)
        return await fn(*args, **kwargs)
    wrapper.__name__ = getattr(fn, "__name__", "wrapped_on_message")
    return wrapper

class ChannelPolicyGateOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _late(self):
        await asyncio.sleep(0)
        wrapped = 0
        for name, cog in list(self.bot.cogs.items()):
            mod = getattr(cog, "__module__", "") or ""
            kind = _kind_for_module(mod)
            if not kind:
                continue
            fn = getattr(cog, "on_message", None)
            if fn and inspect.iscoroutinefunction(fn):
                try:
                    setattr(cog, "on_message", _wrap_on_message(kind, fn))
                    wrapped += 1
                except Exception as e:
                    log.debug("[chan-policy] wrap %s failed: %r", name, e)
        log.info("[chan-policy] active; wrapped=%d", wrapped)

async def setup(bot: commands.Bot):
    cog = ChannelPolicyGateOverlay(bot)
    await bot.add_cog(cog)
    create_task_any(bot, cog._late())
