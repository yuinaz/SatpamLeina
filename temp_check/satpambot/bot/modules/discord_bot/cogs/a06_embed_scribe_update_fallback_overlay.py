
# a06_embed_scribe_update_fallback_overlay.py
from discord.ext import commands
import logging

log = logging.getLogger(__name__)

class EmbedScribeUpdateFallback(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        try:
            from satpambot.bot.utils import embed_scribe as m
        except Exception as e:
            log.debug("[embed-fallback] embed_scribe not available: %r", e)
            return

        if not hasattr(m, "EmbedScribe"):
            log.debug("[embed-fallback] no EmbedScribe symbol")
            return

        ES = m.EmbedScribe
        orig_update = getattr(ES, "update", None)
        orig_post = getattr(ES, "post", None)

        if not callable(orig_post):
            log.debug("[embed-fallback] EmbedScribe.post() missing; nothing to do")
            return

        def _safe_update(self, *a, **kw):
            try:
                # Try original update if exists
                if callable(orig_update):
                    r = orig_update(self, *a, **kw)
                    return r
            except Exception as ex:
                log.debug("[embed-fallback] update raised: %r; falling back to post()", ex)
            # If update path is unavailable or failed, just post a fresh embed
            try:
                return orig_post(self)
            except Exception as ex2:
                log.debug("[embed-fallback] post() failed: %r", ex2)
                return None

        # Install once
        if getattr(ES, "_update_patched_by_fallback", False):
            log.debug("[embed-fallback] already patched")
            return

        if callable(orig_update):
            ES.update = _safe_update
        else:
            # define update that always posts
            ES.update = _safe_update
        setattr(ES, "_update_patched_by_fallback", True)
        log.info("[embed-fallback] EmbedScribe.update patched with safe fallback")
async def setup(bot):
    await bot.add_cog(EmbedScribeUpdateFallback(bot))