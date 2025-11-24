
# a00_selfheal_dedupe_manager.py (v7.5)
# - Disables or dedupes legacy selfheal_autofix extensions so they don't collide
#   with a06_selfheal_autoexec_overlay.
from discord.ext import commands
import asyncio, logging, os

log = logging.getLogger(__name__)

LEGACY_EXTS = [
    "satpambot.bot.modules.discord_bot.cogs.selfheal_autofix",
    "modules.discord_bot.cogs.selfheal_autofix",
    "satpambot.bot.modules.discord_bot.cogs.a00_autoload_selfheal_autofix",
    "modules.discord_bot.cogs.a00_autoload_selfheal_autofix",
]

MODE = os.getenv("SELFHEAL_AUTOFIX_MODE", "disable").lower()  # disable|dedupe|keep

class SelfHealDedupeManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _unload_ext(self, name: str):
        try:
            if name in getattr(self.bot, "extensions", {}):
                await self.bot.unload_extension(name)
                log.info("[selfheal-dedupe] unloaded %s", name)
        except Exception as e:
            log.info("[selfheal-dedupe] unload %s failed: %r", name, e)

    async def _dedupe(self):
        if MODE == "keep":
            log.info("[selfheal-dedupe] MODE=keep — no action")
            return
        # small delay to let autoloaders run
        await asyncio.sleep(0.5)
        exts = list(getattr(self.bot, "extensions", {}).keys())
        has_autoexec = any(x.endswith(".a06_selfheal_autoexec_overlay") for x in exts)
        has_autofix = any(x.endswith("selfheal_autofix") for x in exts)
        log.info("[selfheal-dedupe] ext snapshot: %s", exts)

        if MODE == "disable":
            # remove legacy autofix completely
            for name in exts:
                if name.endswith("selfheal_autofix"):
                    await self._unload_ext(name)
            return

        if MODE == "dedupe" and has_autofix:
            # prefer satpambot path; remove modules.* if present too
            keep = "satpambot.bot.modules.discord_bot.cogs.selfheal_autofix"
            for cand in LEGACY_EXTS:
                if cand != keep and cand in exts:
                    await self._unload_ext(cand)

    @commands.Cog.listener()
    async def on_ready(self):
        await self._dedupe()
async def setup(bot):
    try:
        await bot.add_cog(SelfHealDedupeManager(bot))
    except Exception as e:
        log.info("[selfheal-dedupe] setup swallowed: %r", e)