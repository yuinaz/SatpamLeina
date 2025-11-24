
# a06_embed_scribe_compat_overlay.py (v7.9)
# Provides EmbedScribe.post() shim if not available.
from discord.ext import commands
import logging, asyncio, inspect

log = logging.getLogger(__name__)

class EmbedScribeCompat(commands.Cog):
    def __init__(self, bot): self.bot = bot

    async def _patch(self):
        # Find any object/class named EmbedScribe in loaded cogs/modules and add post()
        for name, cog in list(self.bot.cogs.items()):
            obj = getattr(cog, "scribe", None) or getattr(cog, "embedscribe", None) or getattr(cog, "embed_scribe", None)
            candidates = [obj, getattr(cog, "__class__", None)]
            for cand in candidates:
                if not cand: 
                    continue
                cls = getattr(cand, "__class__", None)
                # prefer class-type if attribute is instance
                target = getattr(cls, "__name__", "") == "EmbedScribe" and cls or None
                if target and not hasattr(target, "post"):
                    async def post(self, *args, **kwargs):
                        up = getattr(self, "upsert", None) or getattr(self, "write", None)
                        if callable(up):
                            res = up(*args, **kwargs)
                            if inspect.isawaitable(res):
                                return await res
                            return res
                        return None
                    setattr(target, "post", post)
                    log.info("[embed-scribe] post() shim installed on %s", target)

    @commands.Cog.listener()
    async def on_ready(self):
        await self._patch()
async def setup(bot):
    await bot.add_cog(EmbedScribeCompat(bot))