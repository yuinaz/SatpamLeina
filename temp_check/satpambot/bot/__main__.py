
import sys
sys.modules.pop('modules', None)
#!/usr/bin/env python3
"""Executable entrypoint for `python -m satpambot.bot`.
Supports sync/async shim_runner entrypoints. Imports are local to dodge ruff I001.
"""

def _run_coro(coro) -> None:
    import asyncio
    try:
        asyncio.run(coro)
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(coro)
        else:
            raise

def _run() -> None:
    import inspect
    try:
        from satpambot.bot.modules.discord_bot import shim_runner as _shim
    except Exception as e:
        raise SystemExit(f"[satpambot.bot.__main__] failed to import shim_runner: {e}")

    for name in ("main", "run", "run_bot", "start", "start_bot"):
        fn = getattr(_shim, name, None)
        if not callable(fn):
            continue
        if inspect.iscoroutinefunction(fn):
            _run_coro(fn()); return
        res = fn()
        if inspect.iscoroutine(res):
            _run_coro(res)
        return
    raise SystemExit("[satpambot.bot.__main__] No suitable entry in shim_runner")

if __name__ == "__main__":
    _run()
