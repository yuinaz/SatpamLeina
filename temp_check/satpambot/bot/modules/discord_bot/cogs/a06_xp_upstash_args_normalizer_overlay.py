from discord.ext import commands

# a06_xp_upstash_args_normalizer_overlay.py (v7.9)
# Normalizes on_satpam_xp(*args, **kwargs) so legacy emitters won't break.
import logging, inspect, asyncio

log = logging.getLogger(__name__)

def _normalize_event(args, kwargs):
    # Accept any of these shapes:
    # (user_id:int, delta:int, reason:str?) OR (member, delta, reason?) OR kwargs={'reason':..}
    uid = None
    delta = None
    reason = kwargs.get("reason")
    if len(args) >= 2:
        a0, a1 = args[0], args[1]
        # Try id
        try:
            uid = int(getattr(a0, "id", a0))
        except Exception:
            uid = None
        try:
            delta = int(a1)
        except Exception:
            delta = None
    elif len(args) == 1:
        try:
            uid = int(getattr(args[0], "id", args[0]))
        except Exception:
            pass
    return uid, delta, reason

class UpstashArgsNormalizer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._task = None

    async def _patch(self):
        # Find target cog by name heuristic
        targets = []
        for name, cog in list(self.bot.cogs.items()):
            if "upstash" in name.lower() and "exact" in name.lower():
                targets.append(cog)
        for cog in targets:
            orig = getattr(cog, "on_satpam_xp", None)
            if not callable(orig):
                continue
            if getattr(cog, "_xp_norm_patched", False):
                continue
            async def wrapper(*args, **kwargs):
                try:
                    uid, delta, reason = _normalize_event(args, kwargs)
                    log.info("[xp-upstash:norm] event normalized: uid=%s delta=%s reason=%s", uid, delta, reason)
                    # Prefer calling original if it accepts flexible signature
                    try:
                        return await orig(*args, **kwargs)  # best effort
                    except TypeError:
                        # fallback: call original with normalized tuple if it supports (uid, delta, reason?)
                        try:
                            arity = len(inspect.signature(orig).parameters)
                        except Exception:
                            arity = 0
                        if arity >= 3:
                            return await orig(uid, delta, reason)
                        elif arity == 2:
                            return await orig(uid, delta)
                        else:
                            # give up gracefully
                            return None
                except Exception as e:
                    log.info("[xp-upstash:norm] wrapper fail: %r", e)
                    return None
            setattr(cog, "on_satpam_xp", wrapper)
            setattr(cog, "_xp_norm_patched", True)
            log.info("[xp-upstash:norm] patched %s", cog.__class__.__name__)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self._task:
            self._task = asyncio.create_task(self._patch())

async def setup(bot):
    await bot.add_cog(UpstashArgsNormalizer(bot))