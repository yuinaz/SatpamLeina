from discord.ext import commands

import logging, importlib

LOG = logging.getLogger(__name__)

def _has_direct(bot): return any(hasattr(bot, n) for n in ("xp_add","xp_award","satpam_xp"))

async def _try_setup(bot, modname):
    try:
        m = importlib.import_module(modname)
        if hasattr(m, "setup"):
            await m.setup(bot)
            LOG.info("[xp-autoload] loaded %s", modname)
            return True
    except Exception as e:
        LOG.debug("[xp-autoload] %s not loaded: %r", modname, e)
    return False

def _attach_minimal(bot):
    async def xp_add(uid, amt, why=None, *a, **kw): bot.dispatch("xp_add", uid, amt, why or "auto")
    async def xp_award(uid, amt, why=None, *a, **kw): bot.dispatch("xp_add", uid, amt, why or "award")
    async def satpam_xp(uid, amt, why=None, *a, **kw): bot.dispatch("satpam_xp", uid, amt, why or "auto")
    for n, fn in (("xp_add", xp_add), ("xp_award", xp_award), ("satpam_xp", satpam_xp)):
        if not hasattr(bot, n): setattr(bot, n, fn)
    LOG.info("[xp-autoload] minimal direct XP methods attached")

class XPDirectAutoload(commands.Cog):
    def __init__(self, bot): self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        if _has_direct(self.bot): return
        for m in (
            "satpambot.bot.modules.discord_bot.cogs.a07_xp_direct_method_shim_overlay",
            "satpambot.bot.modules.discord_bot.cogs.a08_xp_upstash_verbose_overlay",
        ):
            await _try_setup(self.bot, m)
        if not _has_direct(self.bot): _attach_minimal(self.bot)

async def setup(bot): await bot.add_cog(XPDirectAutoload(bot))