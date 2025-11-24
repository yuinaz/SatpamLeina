
from discord.ext import commands
import logging
import os

class _DropDiscord429(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Hide spammy 429 warnings unless explicitly enabled
        msg = record.getMessage()
        if "We are being rate limited" in msg:
            return os.getenv("SHOW_DISCORD_429", "0") == "1"
        return True

class DiscordHttpWarnFilter(commands.Cog):
    """Filter out noisy discord.http 429 warnings (library already retries)."""
    def __init__(self, bot):
        self.bot = bot
        http_logger = logging.getLogger("discord.http")
        http_logger.addFilter(_DropDiscord429())
        # Optional: lower loglevel via env, e.g. DISCORD_HTTP_LOGLEVEL=ERROR
        level = os.getenv("DISCORD_HTTP_LOGLEVEL", "").upper()
        if level in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
            http_logger.setLevel(level)
        logging.getLogger(__name__).info("[warn-filter] discord.http warnings filtered (level=%s)", level or "inherit")
async def setup(bot):
    await bot.add_cog(DiscordHttpWarnFilter(bot))