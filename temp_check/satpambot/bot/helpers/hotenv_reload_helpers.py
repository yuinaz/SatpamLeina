
import asyncio, logging
from typing import Iterable, Optional
from discord.ext.commands import Bot

def reload_extensions_safely(bot: Bot, extensions: Iterable[str], *, logger: Optional[logging.Logger]=None, skip_self: Optional[str]=None):
    log = logger or logging.getLogger(__name__)
    exts = [e for e in extensions if not skip_self or e != skip_self]
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # not in event loop; schedule on default loop
        loop = asyncio.get_event_loop()
    async def _work():
        for ext in exts:
            try:
                await bot.reload_extension(ext)
                log.info("[hotenv] reloaded %s", ext)
            except AttributeError:
                # older discord.py: reload_extension is sync
                bot.reload_extension(ext)  # type: ignore
                log.info("[hotenv] reloaded (sync) %s", ext)
            except Exception as e:
                log.exception("[hotenv] failed reloading %s: %s", ext, e)
    try:
        loop.create_task(_work())
    except Exception:
        # from non-loop thread
        loop.call_soon_threadsafe(lambda: loop.create_task(_work()))
