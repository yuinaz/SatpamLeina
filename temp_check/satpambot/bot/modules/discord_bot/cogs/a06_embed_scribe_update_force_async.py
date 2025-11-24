from __future__ import annotations

"""
EmbedScribe async wrapper:
- Ensures EmbedScribe.update/post/edit are awaitable even if the original is sync.
- Avoids 'object NoneType can't be used in await expression' in callers.
"""

import logging, inspect, asyncio

log = logging.getLogger(__name__)

async def _awaitable_call(fn, *a, **k):
    try:
        res = fn(*a, **k)
        if inspect.isawaitable(res):
            return await res
        return res
    except Exception as e:
        log.warning("[embedscribe-async] call failed: %r", e)
        raise
async def setup(bot):
    try:
        from satpambot.bot.utils.embed_scribe import EmbedScribe
    except Exception as e:
        log.warning("[embedscribe-async] cannot import EmbedScribe: %r", e)
        return

    if getattr(EmbedScribe, "__force_async_patched__", False):
        log.info("[embedscribe-async] already patched")
        return

    for name in ("update", "post", "edit"):
        if not hasattr(EmbedScribe, name):
            continue
        orig = getattr(EmbedScribe, name)

        async def wrapper(self, *a, __orig=orig, **k):
            return await _awaitable_call(__orig, self, *a, **k)

        setattr(EmbedScribe, name, wrapper)
    EmbedScribe.__force_async_patched__ = True
    log.info("[embedscribe-async] wrapped update/post/edit as async")