
from discord.ext import commands
import os, logging, importlib, inspect

LOG = logging.getLogger(__name__)
ENABLE = os.getenv("SELFHEAL_QUORUM_ENABLE", "1") == "1"

class _QuietQuorum:
    targets = ("_execute_plan","_apply_plan","execute_plan","apply_plan","_loop")
    @classmethod
    def pick_target(cls, Cog):
        for name in cls.targets:
            if hasattr(Cog, name):
                fn = getattr(Cog, name)
                if inspect.iscoroutinefunction(fn):
                    return name, fn
        return None, None

class SelfHealQuorumOverlay(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not ENABLE:
            return
        try:
            M = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.selfheal_groq_agent")
        except Exception as e:
            LOG.debug("[quorum-overlay] import selfheal_groq_agent failed: %r", e)
            return
        Cog = getattr(M, "SelfHealGroqAgent", None) or getattr(M, "SelfHealRuntime", None)
        if not Cog:
            return
        name, fn = _QuietQuorum.pick_target(Cog)
        if not name or getattr(fn, "__quiet_quorum__", False):
            return

        async def wrapped(self, *args, **kwargs):
            # keep behavior; gating may live elsewhere
            return await fn(self, *args, **kwargs)

        setattr(wrapped, "__quiet_quorum__", True)
        setattr(Cog, name, wrapped)
async def setup(bot):
    await bot.add_cog(SelfHealQuorumOverlay(bot))