
import asyncio
import inspect
from typing import Iterable, Optional

try:
    import logging
    log = logging.getLogger(__name__)
except Exception:  # pragma: no cover
    log = None

async def _maybe_await(x):
    """Await x if it's awaitable; otherwise return as-is."""
    if inspect.isawaitable(x):
        return await x
    return x

def _kick_to_loop(loop: asyncio.AbstractEventLoop, coro):
    """Run coroutine in the provided loop from any thread.

    Returns:
        - asyncio.Task when already inside loop
        - concurrent.futures.Future when scheduled thread-safely
    """
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None

    if running and running is loop:
        return asyncio.create_task(coro)
    else:
        return asyncio.run_coroutine_threadsafe(coro, loop)

async def _reload_one(bot, ext: str, logger=None):
    """Reload a single extension, handling sync/async API variants safely."""
    try:
        res = bot.reload_extension(ext)
        await _maybe_await(res)
        if logger:
            logger.info("[hotenv] reloaded %s", ext)
    except Exception as e:  # pragma: no cover
        if logger:
            logger.exception("[hotenv] failed to reload %s", ext)
        else:
            # best-effort fallback log
            print(f"[hotenv] failed to reload {ext}: {e!r}")

def reload_extensions_safely(bot, exts: Iterable[str], *, logger: Optional[object] = None, skip_self: Optional[str] = None):
    """Public helper: schedule a safe, version-agnostic mass reload.

    Usage:
        from satpambot.bot.modules.discord_bot.helpers.hotenv_reload_helpers import reload_extensions_safely
        reload_extensions_safely(self.bot, exts, logger=log, skip_self=__name__)
    """
    exts = list(exts or [])
    if skip_self and skip_self in exts:
        try:
            exts.remove(skip_self)
        except ValueError:
            pass

    async def runner():
        await asyncio.gather(*[_reload_one(bot, ext, logger=logger) for ext in exts], return_exceptions=True)

    return _kick_to_loop(bot.loop, runner())
