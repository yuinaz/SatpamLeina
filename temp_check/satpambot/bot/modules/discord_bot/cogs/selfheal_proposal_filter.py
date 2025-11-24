"""
selfheal_proposal_filter.py (patched)
- Menyaring proposal self-heal agar tidak spam & tidak salah deteksi.
- Drop proposal non-kritis secara default (bisa diubah via ENV).
- Khusus action enable_cog/load_cog: kalau cog sudah loaded => drop.
- Jika DM_MUZZLE aktif, arahkan output ke log channel (biar tidak DM).
"""
from __future__ import annotations

import os
from typing import Any, Dict

try:
    # aslinya router punya fungsi send_selfheal; kita bungkus
    from .selfheal_router import send_selfheal as _raw_send_selfheal  # type: ignore
except Exception:
    _raw_send_selfheal = None  # type: ignore

def _env_bool(name: str, default: bool = True) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v not in ("0","false","False","no","NO")

DROP_NONCRITICAL = _env_bool("SELFHEAL_DROP_NONCRITICAL", True)
DROP_ENABLE_IF_LOADED = _env_bool("DROP_ENABLE_COG_IF_LOADED", True)
QUIET_DM = os.getenv("DM_MUZZLE", "") not in ("", "0", "false", "False")

async def send_selfheal(bot, proposal: Dict[str, Any]):  # type: ignore
    """Wrapper yang dipanggil oleh sistem self-heal saat ingin mengirim proposal.
    Return dict status supaya upstream bisa log tanpa raise.
    """
    try:
        action = (proposal.get("action") or proposal.get("type") or "").strip()
        target = (proposal.get("cog") or proposal.get("target") or "").strip()
        critical = bool(proposal.get("critical", False))

        # 1) Drop yang non-kritis (default on)
        if DROP_NONCRITICAL and not critical:
            return {"status": "DROPPED", "reason": "noncritical"}

        # 2) Kalau proposal minta enable_cog tapi cog sudah loaded => drop
        if DROP_ENABLE_IF_LOADED and action in ("enable_cog", "load_cog"):
            try:
                if target and bot.get_cog(target):
                    return {"status": "DROPPED", "reason": f"already_loaded:{target}"}
            except Exception:
                # fallback aman kalau get_cog error
                pass

        # 3) Kalau DM dimuzzle, beri hint ke router supaya ke log
        if QUIET_DM:
            proposal.setdefault("channel_hint", "log")

        if _raw_send_selfheal is None:
            return {"status": "FAILED", "error": "router_unavailable"}
        return await _raw_send_selfheal(bot, proposal)
    except Exception as e:
        return {"status": "FAILED", "error": repr(e)}