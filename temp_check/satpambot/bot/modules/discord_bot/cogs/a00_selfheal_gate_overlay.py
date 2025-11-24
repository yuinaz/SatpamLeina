
from __future__ import annotations
import os, time, logging
from typing import Optional
from discord import Embed

# We will wrap EmbedScribe.upsert to throttle "Self-Heal" notifications
try:
    from satpambot.bot.modules.discord_bot.helpers.embed_scribe import EmbedScribe
except Exception as e:
    EmbedScribe = None

log = logging.getLogger(__name__)

_MARKERS = {"self-heal", "selfheal", "Self-Heal", "Self‑Heal", "Self Heal"}
_TITLES  = {"Self-Heal Note", "Self-Heal Plan", "Maintenance"}

_COOLDOWN = int(os.getenv("SELFHEAL_NOTIFY_COOLDOWN_SEC", "900"))  # 15 minutes default
_state = {"last": 0}

def _is_selfheal_message(content: Optional[str], embed: Optional[Embed]) -> bool:
    c = (content or "").lower()
    if any(m.lower() in c for m in _MARKERS):
        return True
    if embed:
        t = (getattr(embed, "title", "") or "")
        if t in _TITLES:
            return True
    return False

if EmbedScribe is not None and not getattr(EmbedScribe, "_selfheal_wrapped", False):
    _orig_upsert = EmbedScribe.upsert

    @classmethod
    async def upsert(cls, bot, channel_id: int, content: str = "", embed: Optional[Embed] = None,
                     marker: str = None, pin: bool = False, message_id: int = None):
        try:
            if _is_selfheal_message(content, embed):
                now = time.time()
                if (_state["last"] and now - _state["last"] < _COOLDOWN):
                    # swallow this self-heal update (cooldown active)
                    log.info("[selfheal-gate] swallowed self-heal note (cooldown %ss)", _COOLDOWN)
                    return message_id or None
                _state["last"] = now
        except Exception:
            pass
        return await _orig_upsert(bot, channel_id, content=content, embed=embed, marker=marker, pin=pin, message_id=message_id)

    EmbedScribe.upsert = upsert
    EmbedScribe._selfheal_wrapped = True
    log.info("[selfheal-gate] enabled (cooldown=%ss)", _COOLDOWN)

async def setup(bot):
    # overlay doesn't need to add a Cog — it's enough to patch on import
    return
