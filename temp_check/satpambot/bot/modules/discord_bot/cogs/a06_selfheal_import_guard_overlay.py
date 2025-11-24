from __future__ import annotations

import logging, importlib
log = logging.getLogger(__name__)
try:
    pkg = importlib.import_module("satpambot.bot.modules.discord_bot.cogs")
    if not hasattr(pkg, "selfheal_router"):
        class _Noop: pass
        setattr(pkg, "selfheal_router", _Noop())
        log.info("[selfheal_import_guard] provided noop selfheal_router")
except Exception as e:
    log.warning("[selfheal_import_guard] failed to guard: %s", e)