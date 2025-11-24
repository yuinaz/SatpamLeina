from __future__ import annotations

import logging, functools
from typing import Iterable, Set
from satpambot.config.local_cfg import cfg

log = logging.getLogger(__name__)

def _parse_ids(s: str) -> Set[int]:
    xs = []
    if isinstance(s, (list, tuple)): xs = s
    else:
        s = (s or "").replace(",", " ")
        xs = [t for t in s.split() if t.strip()]
    out = set()
    for t in xs:
        try: out.add(int(t))
        except Exception: pass
    return out

# Defaults fall back to user-provided IDs if config kosong
DEFAULT_QNA = 1426571542627614772          # QnA channel (parent protect threads)
DEFAULT_THREADS = {1425400701982478408,    # neuro-lite progress thread
                   1426397317598154844}    # learning progress thread
DEFAULT_EXEMPT_CHANNELS = {1400375184048787566, DEFAULT_QNA}  # log channel + QnA

EXEMPT_CHANNELS = set(_parse_ids(cfg("AUTO_DELETE_EXEMPT_CHANNEL_IDS", ""))) or set(DEFAULT_EXEMPT_CHANNELS)
EXEMPT_THREADS  = set(_parse_ids(cfg("AUTO_DELETE_EXEMPT_THREAD_IDS", "")))  or set(DEFAULT_THREADS)
QNA_PARENT_ID   = int(cfg("LEARNING_QNA_CHANNEL_ID", DEFAULT_QNA) or DEFAULT_QNA)

def _is_exempt_message(msg) -> bool:
    try:
        ch_id = getattr(getattr(msg, "channel", None), "id", None)
        th_id = getattr(getattr(msg, "channel", None), "id", None)
        if th_id in EXEMPT_THREADS: return True
        if ch_id in EXEMPT_CHANNELS: return True
        # parent-protect: if in a Thread di bawah QnA, cegah delete
        parent = getattr(getattr(msg, "channel", None), "parent", None)
        if parent and getattr(parent, "id", None) == QNA_PARENT_ID:
            return True
    except Exception:
        pass
    return False

def _is_exempt_channel(ch) -> bool:
    try:
        if getattr(ch, "id", None) in EXEMPT_CHANNELS: return True
        if getattr(ch, "id", None) in EXEMPT_THREADS: return True
        parent = getattr(ch, "parent", None)
        if parent and getattr(parent, "id", None) == QNA_PARENT_ID: return True
    except Exception:
        pass
    return False

def _patch_delete():
    try:
        import discord
        orig_delete = discord.message.Message.delete
        async def delete_wrap(self, *a, **kw):
            if _is_exempt_message(self):
                log.debug("[autodel_exempt] block Message.delete in exempt area")
                return  # silently ignore
            return await orig_delete(self, *a, **kw)
        discord.message.Message.delete = delete_wrap  # type: ignore[attr-defined]
        log.info("[autodel_exempt] Message.delete patched")
    except Exception as e:
        log.warning("[autodel_exempt] patch delete failed: %s", e)


def _patch_purge():
    try:
        import discord  # type: ignore
    except Exception as e:
        # No discord in runtime; skip silently
        log.info("[autodel_exempt] purge patch skipped (discord not available)")
        return

    patched = False

    # Prefer patching the abstract Messageable interface if it exposes 'purge'
    try:
        abc_mod = getattr(discord, "abc", None)
        target_cls = getattr(abc_mod, "Messageable", None)
        orig_purge = getattr(target_cls, "purge", None) if target_cls is not None else None
        if callable(orig_purge):
            async def purge_wrap(self, *a, **kw):
                if _is_exempt_channel(self):
                    log.debug("[autodel_exempt] block purge in exempt area")
                    return []
                return await orig_purge(self, *a, **kw)
            setattr(target_cls, "purge", purge_wrap)  # type: ignore[attr-defined]
            log.info("[autodel_exempt] purge patched (Messageable)")
            patched = True
    except Exception as e:
        # If patching Messageable fails unexpectedly, keep running; try TextChannel next
        log.warning("[autodel_exempt] purge patch (Messageable) failed: %s", e)

    # Fallback: patch TextChannel.purge if available
    if not patched:
        try:
            tc_cls = getattr(discord, "TextChannel", None)
            orig_purge_tc = getattr(tc_cls, "purge", None) if tc_cls is not None else None
            if callable(orig_purge_tc):
                async def purge_wrap_tc(self, *a, **kw):
                    if _is_exempt_channel(self):
                        log.debug("[autodel_exempt] block purge in exempt area")
                        return []
                    return await orig_purge_tc(self, *a, **kw)
                setattr(tc_cls, "purge", purge_wrap_tc)  # type: ignore[attr-defined]
                log.info("[autodel_exempt] purge patched (TextChannel)")
                patched = True
        except Exception as e:
            log.warning("[autodel_exempt] purge patch (TextChannel) failed: %s", e)

    if not patched:
        # Nothing to patch in this discord.py build -> that's fine; be quiet.
        log.info("[autodel_exempt] purge patch skipped (not supported in this build)")

# ---- auto-added by patch: async setup stub for overlay ----
async def setup(bot):
    return