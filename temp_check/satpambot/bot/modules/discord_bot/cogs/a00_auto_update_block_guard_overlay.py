
# a00_auto_update_block_guard_overlay.py
# Blocks the AutoUpdateManager cog (which runs pip list on startup and can hang)
# unless AUTO_UPDATE_ENABLE=1. Safe to leave permanently.

import os
import logging
from discord.ext import commands

_PATCH_FLAG = "_patched_by_auto_update_block_guard"
_ENABLE = os.getenv("AUTO_UPDATE_ENABLE", "0") == "1"

def _patch_add_cog():
    Bot = commands.Bot
    if getattr(Bot.add_cog, _PATCH_FLAG, False):
        return

    original_add_cog = Bot.add_cog

    async def safe_add_cog(self, cog, *args, **kwargs):
        mod = getattr(type(cog), "__module__", "") or ""
        name = type(cog).__name__
        if (not _ENABLE) and ("auto_update_manager" in mod or name.lower().startswith("autoupdate")):
            logging.warning("[autoupdate-block] Skipping %s from %s (AUTO_UPDATE_ENABLE=0)", name, mod)
            return None  # swallow registration
        return await original_add_cog(self, cog, *args, **kwargs)

    safe_add_cog.__dict__[_PATCH_FLAG] = True
    Bot.add_cog = safe_add_cog
    logging.warning("[autoupdate-block] Bot.add_cog patched (enable=%s)", _ENABLE)

def setup_patch():
    try:
        _patch_add_cog()
    except Exception as e:
        logging.exception("[autoupdate-block] patch failed: %r", e)

setup_patch()

async def setup(bot):
    logging.debug("[autoupdate-block] overlay setup complete")
