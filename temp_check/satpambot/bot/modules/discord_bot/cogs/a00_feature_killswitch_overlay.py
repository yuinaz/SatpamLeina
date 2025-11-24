import os, logging
from discord.ext import commands

TOKENS = [t.strip().lower() for t in os.getenv("DISABLE_MODULE_PATTERNS","phash,phish,phishash,reseed,ban").split(",") if t.strip()]
LOG = logging.getLogger("killswitch")

def _match(name: str) -> bool:
    low = (name or "").lower()
    return any(tok in low for tok in TOKENS)

class FeatureKillSwitch(commands.Cog):
    """Matikan cogs lama sesuai pola (migrasi ke NIXE)."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._done = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self._done: return
        self._done = True
        removed = []
        for cog_name, cog in list(self.bot.cogs.items()):
            mod = getattr(cog, "__module__", "") if cog else ""
            if _match(cog_name) or _match(mod):
                try:
                    self.bot.remove_cog(cog_name)
                    removed.append((cog_name, mod))
                except Exception as e:
                    LOG.warning("KillSwitch failed to remove %s (%s): %s", cog_name, mod, e)
        if removed:
            LOG.warning("KillSwitch removed %d cogs: %s", len(removed), ", ".join([n for n,_ in removed]))
        try:
            self.bot.remove_cog(self.__class__.__name__)
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(FeatureKillSwitch(bot))
