def summarize():
    ok = {}
    try:
        from satpambot.ml import guard_hooks
        ok['guard_hooks_has_get_health'] = hasattr(guard_hooks, 'get_health')
    except Exception:
        ok['guard_hooks_has_get_health'] = False
    return ok
