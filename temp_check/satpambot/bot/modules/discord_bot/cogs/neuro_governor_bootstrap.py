"""
Cog bootstrap: neuro_governor_bootstrap
Loads the staged neuro governor cogs when NEURO_GOVERNOR_ENABLE=1.
Keeps imports lazy to avoid psutil dependency unless enabled.
"""
from __future__ import annotations

from discord.ext import commands

import os, logging, importlib
from satpambot.config.local_cfg import cfg_bool
from typing import Any

log = logging.getLogger(__name__)

async def _maybe_import(module: str):
    try:
        return importlib.import_module(module)
    except Exception as e:
        log.exception("[neuro_gov_bootstrap] import failed for %s: %r", module, e)
        raise
async def setup(bot: commands.Bot):
    flag = cfg_bool("NEURO_GOVERNOR_ENABLE", False) or ((os.getenv("NEURO_GOVERNOR_ENABLE") or "").lower() in {"1","true","yes","on"})
    if not flag:
        log.info("[neuro_gov_bootstrap] disabled (NEURO_GOVERNOR_ENABLE not set)")
        return

    log.warning("[neuro_gov_bootstrap] enabling Neuro Governor…")
    # Import resource_governor lazily to surface psutil errors only when enabled
    try:
        importlib.import_module("satpambot.ai.resource_governor")
    except Exception as e:
        log.exception("[neuro_gov_bootstrap] resource_governor import failed: %r", e)
        raise

    # Load the staged cogs and delegate to their setup()
    gov = await _maybe_import("satpambot.bot.modules.discord_bot.cogs_staging.neuro_governor")
    bridge = await _maybe_import("satpambot.bot.modules.discord_bot.cogs_staging.neuro_governor_bridge")

    # Both files should expose `setup(bot)`
    if hasattr(gov, "setup"):
        await gov.setup(bot)  # type: ignore
    if hasattr(bridge, "setup"):
        await bridge.setup(bot)  # type: ignore

    log.warning("[neuro_gov_bootstrap] Neuro Governor loaded.")