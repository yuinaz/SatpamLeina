from discord.ext import commands
import importlib

class LlmProviderBootstrapQuietOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        try:
            prov = importlib.import_module("satpambot.bot.llm_providers")
            ask_fn = getattr(prov, "ask", None)
            if ask_fn and not hasattr(bot, "llm_ask"):
                bot.llm_ask = ask_fn
        except Exception:
            pass
async def setup(bot):
    await bot.add_cog(LlmProviderBootstrapQuietOverlay(bot))