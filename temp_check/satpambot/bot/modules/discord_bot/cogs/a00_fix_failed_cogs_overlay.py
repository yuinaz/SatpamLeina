from discord.ext import commands
import logging

log = logging.getLogger(__name__.split(".")[-1])

async def _safe_add(bot: commands.Bot, cog_obj):
    try:
        # Skip if cog already loaded
        name = type(cog_obj).__name__
        if bot.get_cog(name):
            log.info("[failed_cogs_fix] skip add already loaded: %s", name)
            return False
        ret = bot.add_cog(cog_obj)
        if hasattr(ret, "__await__"):
            await ret
        log.info("[failed_cogs_fix] loaded %s", name)
        return True
    except Exception as e:
        # Downgrade to INFO to avoid scary WARNING noise on healthy boots
        log.info("add_cog skipped/failed for %s: %r", type(cog_obj).__name__, e)
        return False

async def _try_add(bot: commands.Bot, mod_name: str, cls_name: str) -> bool:
    try:
        # Skip if another module already provided a cog with same class name
        if bot.get_cog(cls_name):
            log.info("[failed_cogs_fix] already present: %s", cls_name)
            return False
        mod = __import__(mod_name, fromlist=[cls_name])
        cls = getattr(mod, cls_name, None)
        if cls is None:
            return False
        cog = cls(bot) if "bot" in getattr(cls, "__init__", (lambda: None)).__code__.co_varnames else cls()
        return await _safe_add(bot, cog)
    except Exception as e:
        log.info("import/add skipped: %s.%s -> %r", mod_name, cls_name, e)
        return False
async def setup(bot: commands.Bot):
    candidates = [
        ("satpambot.bot.modules.discord_bot.cogs.learning_passive_observer", "LearningPassiveObserver"),
        ("satpambot.bot.modules.discord_bot.cogs.learning_passive_observer_persist", "LearningPassiveObserver"),
        ("satpambot.bot.modules.discord_bot.cogs.phish_log_sticky_example", "PhishLogStickyExample"),
        ("satpambot.bot.modules.discord_bot.cogs.phish_log_sticky_guard", "PhishLogStickyGuard"),
        ("satpambot.bot.modules.discord_bot.cogs.qna_dual_provider", "QnaDualProvider"),
        ("modules.discord_bot.cogs.learning_passive_observer", "LearningPassiveObserver"),
        ("modules.discord_bot.cogs.learning_passive_observer_persist", "LearningPassiveObserver"),
        ("modules.discord_bot.cogs.phish_log_sticky_example", "PhishLogStickyExample"),
        ("modules.discord_bot.cogs.phish_log_sticky_guard", "PhishLogStickyGuard"),
        ("modules.discord_bot.cogs.qna_dual_provider", "QnaDualProvider"),
    ]
    for mod, cls in candidates:
        await _try_add(bot, mod, cls)