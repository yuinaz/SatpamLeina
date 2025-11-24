# -*- coding: utf-8 -*-
from __future__ import annotations

from discord.ext import commands

import asyncio, logging, random, discord

from satpambot.bot.modules.discord_bot.config.self_learning_cfg import HTTP_429_MAX_RETRY

log = logging.getLogger(__name__)

def _parse_retry_after(ex):
    try:
        h = ex.response.headers  # type: ignore[attr-defined]
        if not h: return 0.0
        for key in ("Retry-After", "X-RateLimit-Reset-After", "x-ratelimit-reset-after"):
            if key in h:
                try: return float(h.get(key, "0"))
                except: continue
    except Exception:
        pass
    return 3.0

def patch_http_429_backoff():
    orig_request = discord.http.HTTPClient.request
    async def _request(self, route, **kwargs):
        tries = 0
        while True:
            try:
                return await orig_request(self, route, **kwargs)
            except discord.HTTPException as ex:
                if getattr(ex, "status", None) == 429 and tries < HTTP_429_MAX_RETRY:
                    tries += 1
                    wait = _parse_retry_after(ex)
                    jitter = random.uniform(0.15, 0.45)
                    total = max(0.5, wait + jitter)
                    log.warning("[http_429_backoff] 429 on %s — sleep %.2fs (try %s/%s)",
                                getattr(route, "path", route), total, tries, HTTP_429_MAX_RETRY)
                    await asyncio.sleep(total)
                    continue
                raise
    discord.http.HTTPClient.request = _request
    log.info("[http_429_backoff] patched (max_retry=%s)", HTTP_429_MAX_RETRY)

class HTTP429Backoff(commands.Cog):
    def __init__(self, bot): self.bot=bot
    async def cog_load(self): patch_http_429_backoff()
async def setup(bot): await bot.add_cog(HTTP429Backoff(bot))