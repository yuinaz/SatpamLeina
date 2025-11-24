from discord.ext import commands
import asyncio, logging, os, sys

log = logging.getLogger(__name__)

class AutoUpdateGate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.enabled = False  # default off

    async def run_smoke(self) -> bool:
        try:
            if not os.path.exists("scripts/smoke_cogs_micro.py"):
                return True
            proc = await asyncio.create_subprocess_exec(sys.executable, "scripts/smoke_cogs_micro.py")
            rc = await proc.wait()
            log.info("[update-gate] micro-smoke rc=%s", rc)
            return rc == 0
        except Exception as e:
            log.warning("[update-gate] smoke failed: %r", e)
            return False
async def setup(bot):
    await bot.add_cog(AutoUpdateGate(bot))