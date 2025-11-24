
# a00_upstash_block_bucket_overlay.py
from discord.ext import commands
"""
Prevents accidental writes to disallowed Upstash keys (e.g., xp:bucket:*).
Non-invasive: only blocks, never writes.
Control via env:
  XP_UPSTASH_DENY_PREFIX: comma-separated prefixes (default: "xp:bucket:")
"""
import os, logging, inspect

log = logging.getLogger(__name__)

def _env(k, d=None):
    v = os.environ.get(k)
    return v if v not in (None, "") else d

DENY = tuple([p.strip() for p in (_env("XP_UPSTASH_DENY_PREFIX","xp:bucket:").split(",")) if p.strip()])

def _blocked(key: str) -> bool:
    if not key:
        return False
    for p in DENY:
        if key.startswith(p):
            return True
    return False

def _wrap_call(fn):
    async def _wrapped(*a, **kw):
        # Detect "key" positionally or in json/args
        # We try common patterns of provider helpers
        key = kw.get("key")
        if key is None and a:
            # heuristics: first str arg often the key
            for x in a:
                if isinstance(x, str):
                    key = x
                    break
        if isinstance(key, str) and _blocked(key):
            log.info("[upstash-block] blocked write to %s", key)
            # behave like a no-op OK
            return {"result": "OK", "blocked": True}
        return await fn(*a, **kw)
    return _wrapped

class UpstashBlockBucketOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # Try patching known providers
        targets = [
            "satpambot.bot.kv.providers.upstash_rest",
            "satpambot.kv.providers.upstash_rest",
            "satpambot.bot.modules.discord_bot.kv.providers.upstash_rest",
        ]
        for modname in targets:
            try:
                mod = __import__(modname, fromlist=["*"])
            except Exception:
                continue
            # Wrap high-level helpers if present
            for name in ("incrby", "incr", "set_json", "set_str", "upstash"):
                fn = getattr(mod, name, None)
                if fn and inspect.iscoroutinefunction(fn):
                    setattr(mod, name, _wrap_call(fn))
            log.info("[upstash-block] guard active on %s (deny=%s)", modname, ",".join(DENY))
async def setup(bot):
    await bot.add_cog(UpstashBlockBucketOverlay(bot))