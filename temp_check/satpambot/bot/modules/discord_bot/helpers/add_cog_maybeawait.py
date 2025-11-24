# Drop-in helper: maybe_await lifecycle saat add_cog di harness smoke.
import inspect

def add_cog_maybeawait(bot, cog):
    add = getattr(bot, "add_cog", None)
    if add:
        res = add(cog)
        if inspect.isawaitable(res):
            # NOTE: dipakai hanya bila dipanggil dari konteks async
            return res
    cl = getattr(cog, "cog_load", None)
    if cl:
        r = cl()
        if inspect.isawaitable(r):
            return r
    return None
