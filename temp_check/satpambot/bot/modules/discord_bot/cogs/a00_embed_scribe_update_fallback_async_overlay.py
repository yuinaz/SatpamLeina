from discord.ext import commands
import inspect

from satpambot.bot.utils.embed_scribe import EmbedScribe

class EmbedScribeUpdateFallbackAsyncOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Patch sekali saja
        if not getattr(EmbedScribe, "_leina_safe_update_patched", False):
            orig = getattr(EmbedScribe, "update", None)
            if orig is not None:
                def safe_update(self, *args, **kwargs):
                    res = orig(self, *args, **kwargs)
                    if inspect.isawaitable(res):
                        return res
                    async def _noop():
                        return res
                    return _noop()
                EmbedScribe.update = safe_update
                EmbedScribe._leina_safe_update_patched = True

    @commands.Cog.listener()
    async def on_ready(self):
        pass
async def setup(bot):
    await bot.add_cog(EmbedScribeUpdateFallbackAsyncOverlay(bot))