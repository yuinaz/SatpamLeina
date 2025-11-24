from __future__ import annotations

# Bridge entry for MONO run: keeps existing behavior, no config changes.
import asyncio

async def start_bot():
    from satpambot.bot.modules.discord_bot.discord_bot import start_bot as _start
    return await _start()

def main():
    from satpambot.bot.modules.discord_bot.discord_bot import run_bot as _run
    return _run()

if __name__ == "__main__":
    # Allow running directly: python -m satpambot.main
    main()
