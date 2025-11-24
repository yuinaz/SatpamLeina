
# a00_import_compat_alias_overlay.py (v7.5)
from discord.ext import commands
import sys, importlib, logging

log = logging.getLogger(__name__)

def _alias(path: str, target: str) -> bool:
    try:
        mod = importlib.import_module(target)
        sys.modules[path] = mod
        return True
    except Exception as e:
        log.info("[import-alias] cannot alias %s -> %s: %r", path, target, e)
        return False

def _alias_submods(pairs):
    for src, dst in pairs:
        try:
            if dst in sys.modules:
                sys.modules[src] = sys.modules[dst]
                log.info("[import-alias] submodule %s -> %s", src, dst)
        except Exception as e:
            log.info("[import-alias] submodule alias fail %s -> %s: %r", src, dst, e)

class ImportCompatAlias(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        ok1 = _alias("modules", "satpambot.bot.modules")
        ok2 = _alias("modules.discord_bot", "satpambot.bot.modules.discord_bot")
        ok3 = _alias("modules.discord_bot.cogs", "satpambot.bot.modules.discord_bot.cogs")
        # common submodules that often double-load
        _alias_submods([
            ("modules.discord_bot.cogs.selfheal_autofix", "satpambot.bot.modules.discord_bot.cogs.selfheal_autofix"),
            ("modules.discord_bot.cogs.a00_autoload_selfheal_autofix", "satpambot.bot.modules.discord_bot.cogs.a00_autoload_selfheal_autofix"),
        ])
        log.info("[import-alias] compat active: modules=%s discord_bot=%s cogs=%s", ok1, ok2, ok3)
async def setup(bot):
    try:
        await bot.add_cog(ImportCompatAlias(bot))
    except Exception as e:
        log.info("[import-alias] setup swallowed: %r", e)