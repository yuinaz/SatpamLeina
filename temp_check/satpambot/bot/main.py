import asyncio, logging, os, time, traceback, inspect
try:
    from .modules.discord_bot.shim_runner import start_bot
except Exception:
    from satpambot.bot.modules.discord_bot.shim_runner import start_bot  # type: ignore

logging.basicConfig(level=os.environ.get("LOG_LEVEL","INFO"))
log = logging.getLogger("satpambot.bot.main")

async def _run_once():
    # start_bot may be an async function (coroutine) or in rare cases a sync shim.
    # Call it and await only if it's awaitable to avoid "None is not awaitable" errors
    try:
        res = start_bot()
    except TypeError:
        # start_bot might be a coroutine function descriptor or not callable; try calling without args
        res = start_bot

    if inspect.isawaitable(res):
        await res
    else:
        # not awaitable — assume it's a sync function that already ran or returned None
        return

def main():
    backoff = 5  # seconds, doubles up to 60s

    async def _runner():
        nonlocal backoff
        while True:
            try:
                log.info("🤖 Starting Discord bot process...")
                await _run_once()
                log.warning("Bot returned gracefully; restarting in 3s...")
                await asyncio.sleep(3)
                backoff = 5
            except Exception as e:
                log.error("Bot crashed: %s\n%s", e, traceback.format_exc())
                log.info("Restarting in %ss...", backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    asyncio.run(_runner())

if __name__ == "__main__":
    main()
