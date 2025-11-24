
# a06_upstash_intish_parser_overlay.py (v7.9)
# Makes _fetch_state_from_upstash robust to JSON-ish values.
from discord.ext import commands
import logging, json, asyncio

log = logging.getLogger(__name__)

def _intish(x, default=0):
    if x is None:
        return default
    if isinstance(x, (int, float)):
        try: return int(x)
        except: return default
    s = str(x).strip()
    # Try plain int
    try: return int(s)
    except: pass
    # Try JSON object/dict with known keys
    try:
        obj = json.loads(s)
        for k in ("senior_total_xp", "total", "value", "v"):
            if k in obj:
                try: return int(obj[k])
                except: pass
    except Exception:
        pass
    return default

class UpstashIntishParser(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # nothing to patch explicitly; consumers can import _intish if needed
        log.info("[upstash-intish] active")
async def setup(bot):
    await bot.add_cog(UpstashIntishParser(bot))