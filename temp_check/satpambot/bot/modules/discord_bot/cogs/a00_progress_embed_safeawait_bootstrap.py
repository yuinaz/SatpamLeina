
from discord.ext import commands
import importlib, logging, inspect

LOG = logging.getLogger(__name__)

async def _maybe_await(v):
    if inspect.isawaitable(v):
        return await v
    return v

class ProgressEmbedSafeAwait(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # progress_embed_solo.update
        try:
            m = importlib.import_module("satpambot.bot.modules.discord_bot.helpers.progress_embed_solo")
            if hasattr(m, "update") and not getattr(m.update, "__safeawait__", False):
                orig = m.update
                async def wrapped(*a, **kw):
                    return await _maybe_await(orig(*a, **kw))
                wrapped.__safeawait__ = True
                m.update = wrapped
                LOG.info("[safeawait] patched progress_embed_solo.update")
        except Exception as e:
            LOG.debug("[safeawait] skip progress_embed_solo.update: %r", e)

        # EmbedScribe.upsert
        try:
            s = importlib.import_module("satpambot.bot.modules.discord_bot.helpers.embed_scribe")
            ES = getattr(s, "EmbedScribe", None)
            if ES:
                fn = getattr(ES, "upsert", None)
                if fn and not getattr(fn, "__safeawait__", False):
                    async def up(*a, **kw):
                        return await _maybe_await(fn(*a, **kw))
                    up.__safeawait__ = True
                    setattr(ES, "upsert", up)
                    LOG.info("[safeawait] patched EmbedScribe.upsert")
        except Exception as e:
            LOG.debug("[safeawait] skip EmbedScribe.upsert: %r", e)
async def setup(bot):
    await bot.add_cog(ProgressEmbedSafeAwait(bot))