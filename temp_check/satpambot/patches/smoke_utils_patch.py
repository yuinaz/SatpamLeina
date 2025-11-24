# Monkey‑patch untuk membuat harness lama lebih aman saat smoke.
# Import modul ini sangat awal sebelum load cogs.
import inspect

try:
    from satpambot.bot.modules.discord_bot.helpers import smoke_utils as su  # type: ignore
except Exception:
    su = None

if su is not None and getattr(su, "_smoke_patch_applied", False) is False:
    orig_add_cog = getattr(su.DummyBot, "add_cog", None)

    async def _patched_add_cog(self, cog):
        res = None
        if orig_add_cog is not None:
            res = orig_add_cog(self, cog)
            if inspect.isawaitable(res):
                await res
        cl = getattr(cog, "cog_load", None)
        if cl is not None:
            r = cl()
            if inspect.isawaitable(r):
                await r

    try:
        su.DummyBot.add_cog = _patched_add_cog  # type: ignore
        su._smoke_patch_applied = True  # type: ignore
    except Exception:
        pass
