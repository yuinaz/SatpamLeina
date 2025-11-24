
# a22_miner_interval_runtime_tuner.py
# Runtime tuner to normalize miner intervals without editing miner source files.

from discord.ext import commands
import logging, importlib

log = logging.getLogger(__name__)

TARGETS = {
    "phish_text_hourly_miner": {"period": 300, "start": 35},
    "slang_hourly_miner":      {"period": 300, "start": 40},
}

class MinerIntervalRuntimeTuner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _match_miner_key(self, cog):
        mod = getattr(cog, "__module__", "") or ""
        low = mod.lower()
        for key in TARGETS.keys():
            if key in low:
                return key
        # fallback: class-name contains key without underscores
        name = type(cog).__name__.lower()
        for key in TARGETS.keys():
            if key.replace("_", "") in name.replace("_", ""):
                return key
        return None

    def _retune_cog(self, key: str, cog) -> None:
        targets = TARGETS[key]
        period = targets["period"]
        start  = targets["start"]

        # 1) Change any tasks Loops on the cog
        changed = 0
        for attr_name in dir(cog):
            try:
                attr = getattr(cog, attr_name)
            except Exception:
                continue
            if hasattr(attr, "change_interval") and callable(getattr(attr, "change_interval", None)):
                try:
                    attr.change_interval(seconds=period)
                    changed += 1
                except Exception:
                    pass
        if changed:
            log.info("[interval_tuner] %s: set period -> %ss on %d loop(s)", key, period, changed)
        else:
            log.warning("[interval_tuner] %s: no Loop with change_interval found", key)

        # 2) Adjust instance hints (for future before_loop reads)
        for hint in ("START_DELAY_SEC", "start_delay_sec", "start_delay"):
            if hasattr(cog, hint):
                try:
                    setattr(cog, hint, start)
                    log.info("[interval_tuner] %s: instance.%s -> %ss", key, hint, start)
                except Exception:
                    pass

        # 3) Patch module-level constants (for future imports/restarts)
        try:
            mname = f"satpambot.bot.modules.discord_bot.cogs.{key}"
            m = importlib.import_module(mname)
            if hasattr(m, "PERIOD_SEC"):
                setattr(m, "PERIOD_SEC", period)
                log.info("[interval_tuner] %s: module.PERIOD_SEC -> %ss", key, period)
            if hasattr(m, "START_DELAY_SEC"):
                setattr(m, "START_DELAY_SEC", start)
                log.info("[interval_tuner] %s: module.START_DELAY_SEC -> %ss", key, start)
        except Exception as e:
            log.debug("[interval_tuner] %s: module patch skip: %r", key, e)

    @commands.Cog.listener()
    async def on_ready(self):
        for name, cog in list(self.bot.cogs.items()):
            key = self._match_miner_key(cog)
            if key:
                self._retune_cog(key, cog)

    @commands.Cog.listener()
    async def on_cog_add(self, cog):
        key = self._match_miner_key(cog)
        if key:
            self._retune_cog(key, cog)
async def setup(bot):
    await bot.add_cog(MinerIntervalRuntimeTuner(bot))