# Monkey patch for learning_progress: ensure _slang_counts returns 4-tuple
def apply():
    try:
        from satpambot.bot.modules.discord_bot.cogs import learning_progress as lp
        if hasattr(lp, '_slang_counts'):
            _orig = lp._slang_counts
            def _wrap(*a, **k):
                res = _orig(*a, **k)
                if isinstance(res, tuple) and len(res) == 3:
                    t,p,n = res
                    return t,p,n,False
                return res
            lp._slang_counts = _wrap
    except Exception:
        pass

apply()
