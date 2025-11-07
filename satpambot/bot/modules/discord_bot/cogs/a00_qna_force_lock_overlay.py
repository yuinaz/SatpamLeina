from __future__ import annotations
import os, logging, importlib

# Fail-safe overlay: does not require discord import, never raises at import-time.
log = logging.getLogger(__name__)

ENABLE = os.getenv("QNA_FORCE_LOCK_ENABLE", "1") != "0"
_TRUE = {"1","true","yes","on","y","t"}

def _flag(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    return default if v is None else (str(v).strip().lower() in _TRUE)

def _set(k: str, v) -> None:
    os.environ[k] = str(v)

def _disable_mod(module_name: str) -> bool:
    """Best-effort: turn off known overlay modules if they expose enable flags.
    Never raises; returns True if any flag was toggled.
    """
    try:
        m = importlib.import_module(module_name)
    except Exception:
        return False
    changed = False
    for attr in ("ENABLE", "ENABLED", "ACTIVE", "Active"):
        if hasattr(m, attr):
            try:
                setattr(m, attr, False)
                changed = True
            except Exception:
                pass
    return changed

def _apply_force_lock() -> None:
    if not ENABLE:
        return
    forced = (os.getenv("QNA_FORCE_PROVIDER", "") or "").strip().lower()
    if not forced:
        return
    strict = _flag("QNA_STRICT_FORCE", False)

    # In strict mode, fully disable any cross-provider fallback/autopilot flags
    if strict:
        for k in (
            "QNA_ALLOW_FALLBACK",
            "QNA_ALLOW_FALLBACK_WHEN_FORCED",
            "QNA_AUTOFALLBACK",
            "QNA_AUTOFAILOVER",
            "QNA_AUTOPILOT",
        ):
            _set(k, "0")

    # Disable the opposite provider to avoid accidental use
    if forced == "groq":
        _set("GEMINI_FORCE_DISABLE", "1")
    elif forced == "gemini":
        _set("GROQ_FORCE_DISABLE", "1")

    # Best-effort: disable Leina overlays that might auto-switch providers
    for mod in (
        "satpambot.bot.modules.discord_bot.cogs.a00_qna_provider_autofailover_local_overlay",
        "satpambot.bot.modules.discord_bot.cogs.a00_qna_provider_autofailover_quota_overlay",
        "satpambot.bot.modules.discord_bot.cogs.a24_qna_autopilot_scheduler",
    ):
        _disable_mod(mod)

    log.warning("[qna-force-lock] active forced=%s strict=%s", forced or "-", strict)

# Run once at import (no exceptions propagate)
try:
    _apply_force_lock()
except Exception:
    log.exception("[qna-force-lock] init failed")

async def setup(bot):  # discord.py v2 style; do nothing but keep overlay loadable
    try:
        _apply_force_lock()
    except Exception:
        log.exception("[qna-force-lock] setup failed")
