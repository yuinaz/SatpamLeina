from __future__ import annotations

import logging, pkgutil, importlib, os

logger = logging.getLogger(__name__)

# Skip module basenames by default (sesuai versi awal GitHub)
DEFAULT_SKIP = {"commands_probe"}

# Bisa disable module via ENV tanpa ubah file:
#   DISABLED_COGS="metrics,security_hardening"
DISABLED_COGS = set((os.getenv("DISABLED_COGS") or "image_poster").split(","))

def _iter_cogs_package(package_name: str):
    """Yield fully qualified module names inside a cogs package."""
    try:
        pkg = importlib.import_module(package_name)
    except Exception:
        return []
    try:
        for m in pkgutil.iter_modules(pkg.__path__, package_name + "."):
            yield m.name
    except Exception:
        return []

def _iter_all_candidates():
    # Urutan pencarian sama seperti basis repo-mu
    for base in [
        "satpambot.bot.modules.discord_bot.cogs",
        "modules.discord_bot.cogs",
        "discord_bot.cogs",
    ]:
        for name in _iter_cogs_package(base):
            yield name

async def load_all(bot):
    """Auto-discover & load semua cogs; yang error tidak memblokir lainnya."""
    loaded = set()
    for name in _iter_all_candidates():
        base = name.split(".")[-1]
        if base in loaded or base in DEFAULT_SKIP or base in DISABLED_COGS:
            continue
        try:
            await bot.load_extension(name)
            loaded.add(base)
            logger.info("[cogs_loader] loaded %s", name)
        except Exception:
            # Jangan patahkan startup; cukup log trace di level debug
            logger.debug("[cogs_loader] skip %s", name, exc_info=True)

async def load_cogs(bot):
    # Alias lama (kompatibel)
    return await load_all(bot)


# === additive: safe import helper (no config/env change) ===
import importlib as _importlib
def try_import(modname: str):
    try:
        return _importlib.import_module(modname), None
    except Exception as e:
        return None, f"{modname}: {e.__class__.__name__}: {e}"
