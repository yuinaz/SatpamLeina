try:
    from discord.ext import commands  # type: ignore
except Exception:
    class _Base: pass
    class commands:  # type: ignore
        Cog = _Base
class _DummyCog(commands.Cog):
    def __init__(self, bot): self.bot = bot
async def setup(bot): return None
