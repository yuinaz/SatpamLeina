
from discord.ext import commands
import logging, os, re

DEFAULT_PATTERNS = [
    r"Extension .+ is already loaded",
    r"autoload_.+ is already loaded",
    r"\[warn-filter\]",
    r"SelfHealRuntime",
    r"dm_muzzle.+ACTIVE",
    r"Neuro Governor loaded",
    r"discord http warnings filtered",
]

def _compile_patterns():
    env = os.getenv("LOG_NOISE_PATTERNS", "")
    pats = [p.strip() for p in env.split("|") if p.strip()] or DEFAULT_PATTERNS
    return [re.compile(p, re.I) for p in pats]

class _DropWarnFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self._rxs = _compile_patterns()

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if record.levelno == logging.WARNING:
                msg = record.getMessage()
                for rx in self._rxs:
                    if rx.search(msg):
                        return False
        except Exception:
            pass
        return True

def _install_filters():
    drop = _DropWarnFilter()
    root = logging.getLogger()
    for h in root.handlers:
        h.addFilter(drop)
    logging.getLogger("satpambot").addFilter(drop)
    logging.getLogger("discord").setLevel(logging.ERROR)
    logging.getLogger("httpx").setLevel(logging.ERROR)
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    print("[log-noise-filter] installed")

class LogNoiseFilter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        _install_filters()

    @commands.Cog.listener()
    async def on_ready(self):
        _install_filters()
async def setup(bot):
    await bot.add_cog(LogNoiseFilter(bot))
    print("[log-noise-filter] overlay loaded (WARNING demotion via drop filter)")