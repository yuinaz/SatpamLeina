from __future__ import annotations

import os, importlib

EXTENSIONS = (
    "satpambot.bot.modules.discord_bot.cogs.learning_passive_observer",
    "satpambot.bot.modules.discord_bot.cogs.phish_log_sticky_guard",
)

def _split_csv(val: str | None) -> list[str]:
    if not val: return []
    return [x.strip() for x in val.split(",") if x.strip()]

def _iter_unique(seq):
    seen, out = set(), []
    for s in seq:
        if s not in seen:
            seen.add(s); out.append(s)
    return out

async def load_all(bot):
    enable = _split_csv(os.getenv("COGS_FORCE_ENABLE"))
    disable = set(_split_csv(os.getenv("COGS_FORCE_DISABLE")))
    merged = _iter_unique(list(EXTENSIONS) + enable)
    merged = [m for m in merged if m and m not in disable and not m.endswith(".weekly_xp_guard")]
    for ext in merged:
        try:
            await bot.load_extension(ext)
        except Exception:
            # fallback sync setup
            mod = importlib.import_module(ext)
            if hasattr(mod, "setup"):
                mod.setup(bot)