
# _miner_tuning_overlay.py
# Overlay modul ringan: injeksi limit & skip channel tanpa mengubah file miner asli.
# Dibiarkan tanpa setup() supaya cogs_loader kamu tetap bisa mengimport modul ini ("no setup() — import ok").
from importlib import import_module
import logging

log = logging.getLogger(__name__)

# Channel non-chat yang harus di-skip (permintaan user)
SKIP_CHANNEL_IDS = {
    763813761814495252, 936689852546678885, 767401659390623835, 1270611643964850178,
    761163966482743307, 1422084695692414996, 1372983711771001064, 1378739739930398811,
}

# Konfigurasi aman anti-429 (Cloudflare/Discord)
PER_CHANNEL_LIMIT = 100
TOTAL_BUDGET      = 900
PAGINATE_LIMIT    = 100
MIN_SLEEP_SECONDS = 0.80

PATCHES = [
    # Phish miner
    ("satpambot.bot.modules.discord_bot.cogs.phish_text_hourly_miner", {
        "PHISH_PER_CHANNEL_LIMIT": PER_CHANNEL_LIMIT,
        "PHISH_TOTAL_BUDGET": TOTAL_BUDGET,
        "PHISH_PAGINATE_LIMIT": PAGINATE_LIMIT,
        "PHISH_MIN_SLEEP_SECONDS": MIN_SLEEP_SECONDS,
        "PHISH_SKIP_CHANNEL_IDS": SKIP_CHANNEL_IDS,
    }),
    # Slang miner
    ("satpambot.bot.modules.discord_bot.cogs.slang_hourly_miner", {
        "SLANG_PER_CHANNEL_LIMIT": PER_CHANNEL_LIMIT,
        "SLANG_TOTAL_BUDGET": TOTAL_BUDGET,
        "SLANG_PAGINATE_LIMIT": PAGINATE_LIMIT,
        "SLANG_MIN_SLEEP_SECONDS": MIN_SLEEP_SECONDS,
        "SLANG_SKIP_CHANNEL_IDS": SKIP_CHANNEL_IDS,
    }),
]

def _choose(kv, *names):
    for n in names:
        if n in kv:
            return kv[n]
    return None

for modname, kv in PATCHES:
    try:
        m = import_module(modname)
        applied = {}
        for k, v in kv.items():
            try:
                setattr(m, k, v)
                applied[k] = v
            except Exception as ie:
                log.debug("skip set %s.%s: %r", modname, k, ie)
        per_ch = _choose(kv, "PHISH_PER_CHANNEL_LIMIT", "SLANG_PER_CHANNEL_LIMIT", "TEXT_PER_CHANNEL_LIMIT")
        total  = _choose(kv, "PHISH_TOTAL_BUDGET", "SLANG_TOTAL_BUDGET", "TEXT_TOTAL_BUDGET")
        log.info("[tuning_overlay] %s patched (per_channel=%s total_budget=%s skip=%d)",
                 modname, per_ch, total, len(SKIP_CHANNEL_IDS))
    except Exception as e:
        log.warning("[tuning_overlay] failed to patch %s: %r", modname, e)
