from __future__ import annotations

from discord.ext import commands

import logging
import os
from typing import Set, Optional

import discord

from discord.abc import Messageable

log = logging.getLogger(__name__)

# === module-scope state (bukan atribut channel/thread) ===
_ORIG_SEND = None  # type: ignore
_ALLOWED_IDS: Set[int] = set()
_SYS_THREAD_NAMES: Set[str] = set()
_ENABLED = True


def _parse_ids(raw: Optional[str]) -> Set[int]:
    if not raw:
        return set()
    toks = raw.replace(",", " ").split()
    out = set()
    for t in toks:
        t = t.strip()
        if t.isdigit():
            try:
                out.add(int(t))
            except Exception:
                pass
    return out


def _parse_bool(raw: Optional[str], default: bool = True) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off", "")


def _parse_names(raw: Optional[str]) -> Set[str]:
    if not raw:
        return set()
    return {s.strip().lower() for s in raw.split(",") if s.strip()}


async def _silenced_send(self_msg: Messageable, *args, **kwargs):
    """
    Wrapper utk Messageable.send:
    - Pakai module-scope _ALLOWED_IDS / _SYS_THREAD_NAMES
    - Bypass bila _bypass_silencer=True
    """
    # Bypass manual utk internal call tertentu
    if kwargs.pop("_bypass_silencer", False):
        return await _ORIG_SEND(self_msg, *args, **kwargs)  # type: ignore

    # Kalau dimatikan atau whitelist kosong -> kirim biasa
    if not _ENABLED or not _ALLOWED_IDS:
        return await _ORIG_SEND(self_msg, *args, **kwargs)  # type: ignore

    # Ambil id channel/thread dan parent id
    cid = getattr(self_msg, "id", None)
    pid = getattr(self_msg, "parent_id", None)
    cname = getattr(self_msg, "name", "?")
    gname = getattr(getattr(self_msg, "guild", None), "name", None)

    # Izinkan bila channel atau parent ada di whitelist
    if (isinstance(cid, int) and cid in _ALLOWED_IDS) or (isinstance(pid, int) and pid in _ALLOWED_IDS):
        return await _ORIG_SEND(self_msg, *args, **kwargs)  # type: ignore

    # Izinkan thread "sistem" berdasarkan nama (configurable)
    if isinstance(self_msg, (discord.Thread,)):
        name_lc = (cname or "").lower()
        if name_lc in _SYS_THREAD_NAMES:
            return await _ORIG_SEND(self_msg, *args, **kwargs)  # type: ignore

        # Opsi: kalau thread dibuat oleh bot sendiri, izinkan
        try:
            bot_id = getattr(getattr(self_msg, "guild", None), "me", None)
            bot_id = getattr(bot_id, "id", None)
            if bot_id and getattr(self_msg, "owner_id", None) == bot_id:
                return await _ORIG_SEND(self_msg, *args, **kwargs)  # type: ignore
        except Exception:
            pass

    # Blok & log
    try:
        if gname:
            log.info("[shadow_silencer] blocked send to #%s (guild=%s)", cname, gname)
        else:
            log.info("[shadow_silencer] blocked send to #%s", cname)
    except Exception:
        log.info("[shadow_silencer] blocked send")
    return None  # cukup diam


class ShadowPublicSilencer(commands.Cog):
    """Membatasi pengiriman publik; hanya whitelist yg lolos."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Kumpulkan allowed IDs dari env
        ids: Set[int] = set()
        # LOG_CHANNEL_ID bisa diikutkan otomatis
        log_id_raw = os.getenv("LOG_CHANNEL_ID", "")
        if log_id_raw.strip().isdigit():
            ids.add(int(log_id_raw.strip()))
        # Tambahan: PUBLIC_ALLOWED_IDS (spasi/koma dipisahkan)
        ids |= _parse_ids(os.getenv("PUBLIC_ALLOWED_IDS", ""))

        # Nama-nama thread sistem yang boleh (default include neuro-lite progress)
        sys_names = _parse_names(os.getenv("SYSTEM_THREAD_NAMES", "neuro-lite progress"))

        # Enabled/disabled
        enabled = _parse_bool(os.getenv("PUBLIC_SILENCER_ENABLED", "true"))

        # Commit ke module-scope
        global _ALLOWED_IDS, _SYS_THREAD_NAMES, _ENABLED, _ORIG_SEND
        _ALLOWED_IDS = ids
        _SYS_THREAD_NAMES = sys_names
        _ENABLED = enabled

        log.info("[shadow_silencer] whitelist ids set: %s", list(_ALLOWED_IDS))
        log.info("[shadow_silencer] system thread names: %s", list(_SYS_THREAD_NAMES))
        log.info("[shadow_silencer] active (public allowed? %s)", str(_ENABLED is False))

        # Patch sekali saja
        if _ORIG_SEND is None:
            _ORIG_SEND = Messageable.send  # type: ignore
            Messageable.send = _silenced_send  # type: ignore

    def cog_unload(self):
        # Optional: kembalikan patch saat cog unload
        global _ORIG_SEND
        if _ORIG_SEND is not None:
            Messageable.send = _ORIG_SEND  # type: ignore
            _ORIG_SEND = None
async def setup(bot: commands.Bot):
    await bot.add_cog(ShadowPublicSilencer(bot))