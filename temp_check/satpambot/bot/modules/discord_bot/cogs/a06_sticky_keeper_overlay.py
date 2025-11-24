
# -*- coding: utf-8 -*-
"""
Overlay: StickyKeeper
- Guarantees *single* sticky message per (channel, marker) and edits it instead of posting new ones.
- Patches:
    * log_utils.upsert_status_embed -> sticky aware
    * embed_scribe.upsert           -> sticky aware (non-breaking)
This overlay is safe to ship alongside existing coalescer/pin overlays.
"""
import asyncio
import logging
import inspect

from discord import NotFound
from discord import Embed

from satpambot.bot.modules.discord_bot.helpers import log_utils as _log_utils
from satpambot.bot.utils import embed_scribe as _scribe
from satpambot.bot.modules.discord_bot.helpers import sticky_keeper as _keeper

_logger = logging.getLogger(__name__)

def _embed_hash(embed: Embed) -> str:
    try:
        import hashlib, json
        d = embed.to_dict()
        # normalize dynamic fields that change on every push if any
        d.get('timestamp') and d.__setitem__('timestamp', None)
        raw = json.dumps(d, sort_keys=True, separators=(',',':')).encode('utf-8')
        return hashlib.sha1(raw).hexdigest()
    except Exception:
        return None

async def _sticky_upsert_bridge(channel, *, title: str, embed: Embed,
                                pin: bool = True, edit_only: bool = False,
                                marker: str = None):
    marker = marker or f"sticky:{title}"
    # ensure footer marker so future scans are cheap & reliable
    try:
        ft = (embed.footer.text or "") if embed.footer else ""
        if marker not in ft:
            ft = (ft + "  " if ft else "") + marker
            if embed.footer:
                embed.set_footer(text=ft, icon_url=getattr(embed.footer, "icon_url", None))
            else:
                embed.set_footer(text=ft)
    except Exception:
        pass

    # fast path: id-index
    keeper = await _keeper.fetch_indexed(channel, marker)
    if keeper is None:
        # slow path: search pins/history
        keeper = await _keeper.find_existing(channel, title=title, marker=marker)

    if keeper is not None:
        try:
            # skip identical payloads
            new_h = _embed_hash(embed)
            old_h = _keeper.get_cached_hash(channel, marker)
            if new_h and old_h and new_h == old_h:
                return keeper
            await keeper.edit(embed=embed)
            await _keeper.index(channel, marker, keeper)
            _keeper.set_cached_hash(channel, marker, new_h)
            if pin:
                try:
                    await keeper.pin(reason="sticky")
                except Exception:
                    pass
            return keeper
        except NotFound:
            keeper = None
        except Exception:
            _logger.exception("[sticky] edit failed; will create new if allowed")

    if edit_only:
        return None

    # create new
    msg = await channel.send(embed=embed)
    await _keeper.index(channel, marker, msg)
    _keeper.set_cached_hash(channel, marker, _embed_hash(embed))
    if pin:
        try:
            await msg.pin(reason="sticky")
        except Exception:
            pass
    # cleanup dupes best-effort (older bot messages with same marker)
    asyncio.create_task(_keeper.gc_dupes(channel, title=title, marker=marker, keep=msg.id))
    return msg

# ---- Monkey patches -------------------------------------------------------

_original_scribe_upsert = _scribe.upsert

async def _scribe_upsert_sticky(*args, **kwargs):
    """Drop-in replacement for embed_scribe.upsert.
    We intercept calls that look like sticky-eligible and route to StickyKeeper.
    Fallbacks to the original implementation for non-embeds or unknown patterns.
    Supported call forms:
        upsert(channel, title=..., embed=..., edit_only=..., pinned=...)
    """
    try:
        if not args and 'channel' in kwargs:
            channel = kwargs.get('channel')
        else:
            channel = args[0]
        title = kwargs.get('keeper_title') or kwargs.get('title')
        embed = kwargs.get('embed')
        edit_only = bool(kwargs.get('edit_only', False))
        pin = bool(kwargs.get('pinned', True))
        marker = kwargs.get('marker') or (f"sticky:{title}" if title else None)

        # Only hijack when we have a proper embed + title
        if channel and embed is not None and title:
            return await _sticky_upsert_bridge(channel, title=title, embed=embed, pin=pin, edit_only=edit_only, marker=marker)
    except Exception:
        _logger.exception("[sticky] bridge failed; falling back to original upsert")
    return await _original_scribe_upsert(*args, **kwargs)

# Patch log_utils.upsert_status_embed
_original_upsert_status = _log_utils.upsert_status_embed

async def _upsert_status_embed_sticky(*args, **kwargs):
    try:
        channel = kwargs.get('channel') or (args[0] if args else None)
        embed = kwargs.get('embed') or kwargs.get('e') or (args[1] if len(args) > 1 else None)
        title = kwargs.get('title') or "Periodic Status"
        edit_only = bool(kwargs.get('edit_only', True))
        pin = True
        marker = "sticky:status:v1"
        if channel is not None and embed is not None:
            return await _sticky_upsert_bridge(channel, title=title, embed=embed, pin=pin, edit_only=edit_only, marker=marker)
    except Exception:
        _logger.exception("[sticky] status-embed bridge failed; using original")
    return await _original_upsert_status(*args, **kwargs)

class StickyKeeperOverlay:
    def __init__(self, bot):
        self.bot = bot
        # do patches
        _scribe.upsert = _scribe_upsert_sticky
        _log_utils.upsert_status_embed = _upsert_status_embed_sticky
        _logger.info("[sticky] overlay active (scribe+status patched)")
async def setup(bot):
    await bot.add_cog(StickyKeeperOverlay(bot))

# === sticky keeper safety ===
async def _ensure_keeper(self, channel):
    keeper = getattr(self, "_keeper", None)
    if keeper is None:
        try:
            keeper = await channel.send("🔖 keeper init")
            try:
                await keeper.pin()
            except Exception:
                pass
            self._keeper = keeper
        except Exception:
            return None
    return keeper
