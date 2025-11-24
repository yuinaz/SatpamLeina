# -*- coding: utf-8 -*-
"""
a00_upstash_env_bridge.py
-------------------------
Normalize Render/Upstash env names so downstream cogs can always rely on:
  - UPSTASH_REST_URL
  - UPSTASH_REST_TOKEN
and set UPSTASH_ENABLE=1 when credentials exist.
"""
from discord.ext import commands
import os
import logging

log = logging.getLogger(__name__)

def _alias_env(src_keys, dest_key):
    env = os.environ
    if env.get(dest_key):
        return env[dest_key]
    for k in src_keys:
        v = env.get(k)
        if v:
            env[dest_key] = v
            return v
    return None

class UpstashEnvBridge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.apply()

    def apply(self):
        # Accept both Redis REST and KV REST envs
        url = _alias_env(
            ["UPSTASH_REST_URL", "UPSTASH_REDIS_REST_URL", "UPSTASH_KV_REST_URL"],
            "UPSTASH_REST_URL",
        )
        token = _alias_env(
            ["UPSTASH_REST_TOKEN", "UPSTASH_REDIS_REST_TOKEN", "UPSTASH_KV_REST_TOKEN"],
            "UPSTASH_REST_TOKEN",
        )
        if url and token:
            os.environ.setdefault("UPSTASH_ENABLE", "1")
            shown = (url[:48] + "...") if len(url) > 48 else url
            log.info("[upstash-overlay] enable=%s url=%s token=%s",
                     os.environ.get("UPSTASH_ENABLE"), shown, "set")
        else:
            log.warning("[upstash-overlay] Upstash credentials incomplete (url=%s, token=%s)",
                        bool(url), bool(token))
async def setup(bot):
    await bot.add_cog(UpstashEnvBridge(bot))