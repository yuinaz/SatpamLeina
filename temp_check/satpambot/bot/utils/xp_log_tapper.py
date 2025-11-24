"""
xp_log_tapper.py — Tangkap log XP dari learning_passive_observer dan simpan ke xp_store.

Modul ini memasang logging.Handler ringan yang mem-parsing pesan seperti:
  "[passive-learning] +12 XP -> total=34 level=TK"
dan menyimpan delta XP ke xp_store.json.

Cara pakai: import di bootstrap sangat awal (mis. dari minipc_app.py)
    from satpambot.bot.utils import xp_log_tapper
    xp_log_tapper.install()
"""
from __future__ import annotations

import logging, re
from typing import Optional
from . import xp_store

_INSTALLED = False
_PATTERNS = [
    # Contoh: "[passive-learning] +12 XP -> total=123 level=TK"
    re.compile(r"\+(?P<delta>\d+)\s*XP\s*->\s*total=(?P<total>\d+)(?:\s+level=(?P<level>\S+))?", re.I),
    # Cadangan: "gain 12 XP", "+12XP"
    re.compile(r"(?:gain\s+|\+)(?P<delta>\d+)\s*XP", re.I),
]

class _TapHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = record.getMessage()
            # Fokus pada modul learning_* untuk mengurangi false positive
            family = str(record.name)
            if "learning" not in family and "passive" not in family:
                return
            delta: Optional[int] = None
            level: Optional[str] = None
            for pat in _PATTERNS:
                m = pat.search(msg)
                if m:
                    try:
                        delta = int(m.group("delta"))
                    except Exception:
                        continue
                    level = (m.groupdict().get("level") or None) if hasattr(m, "groupdict") else None
                    break
            if delta is None:
                return
            xp_store.record(delta=delta, src=family, level=level)
        except Exception:
            # Jangan sampai handler ini memecahkan logging utama
            pass

def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True
    xp_store.init()
    h = _TapHandler()
    h.setLevel(logging.INFO)
    root = logging.getLogger()  # pasang di root
    root.addHandler(h)