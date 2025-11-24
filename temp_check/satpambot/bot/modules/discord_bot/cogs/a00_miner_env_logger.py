from discord.ext import commands
import os
import logging

log = logging.getLogger(__name__)

def _g(name, default=None):
    v = os.getenv(name)
    return v if v is not None else default

class MinerEnvLogger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        log.info(
            "[miner_env] profile=%s "
            "TEXT(delay=%s,every=%s) PHISH(delay=%s,every=%s,limit=%s) "
            "SLANG(delay=%s,every=%s,per_channel=%s) report_ch=%s",
            _g("MINER_PROFILE", "balanced"),
            _g("TEXT_MINER_DELAY_SEC", "?"),
            _g("TEXT_MINER_INTERVAL_SEC", "?"),
            _g("PHISH_MINER_DELAY_SEC", "?"),
            _g("PHISH_MINER_INTERVAL_SEC", "?"),
            _g("PHISH_MINER_LIMIT", "?"),
            _g("SLANG_MINER_DELAY_SEC", "?"),
            _g("SLANG_MINER_INTERVAL_SEC", "?"),
            _g("SLANG_MINER_PER_CHANNEL", "?"),
            _g("PUBLIC_REPORT_CHANNEL_ID", _g("LOG_CHANNEL_ID", "?"))
        )
async def setup(bot):
    await bot.add_cog(MinerEnvLogger(bot))