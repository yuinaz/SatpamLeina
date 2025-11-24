from __future__ import annotations

import logging
for n in [
    "satpambot.bot.modules.discord_bot.cogs.selfheal_thread_router",
    "satpambot.bot.modules.discord_bot.cogs.http_429_backoff",
]:
    try: logging.getLogger(n).setLevel(logging.ERROR)
    except Exception: pass