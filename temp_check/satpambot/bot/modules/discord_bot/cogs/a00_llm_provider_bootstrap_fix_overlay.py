
from discord.ext import commands
from satpambot.bot.providers import llm_facade

class LlmBootstrapFixOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # expose as coroutine: bot.llm_ask(prompt, system=None, prefer=None)
        async def _llm_ask(prompt: str, system: str | None = None, prefer: str | None = None):
            prov, text = await llm_facade.ask(prompt, system=system, prefer=prefer)
            return {"provider": prov, "text": text}
        bot.llm_ask = _llm_ask  # unify signature across cogs
async def setup(bot): 
    await bot.add_cog(LlmBootstrapFixOverlay(bot))