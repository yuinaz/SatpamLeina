from __future__ import annotations

import os
import time
import logging

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

def _ebool(k: str, d: bool = False) -> bool:
    v = os.getenv(k)
    if v is None or v == "":
        return d
    return str(v).lower() in ("1","true","yes","on")

def _ids(raw: str | None):
    s = set()
    if not raw:
        return s
    for p in raw.replace(";", ",").split(","):
        p = p.strip()
        if not p:
            continue
        try:
            s.add(int(p))
        except Exception:
            pass
    return s

XP = int(os.getenv("SHADOW_EXPOSURE_XP", "15") or "15")
COOLDOWN = int(os.getenv("SHADOW_XP_COOLDOWN_SEC", "120") or "120")
ENABLE = _ebool("SHADOW_ENABLE", True)

SKIP = _ids(os.getenv("SHADOW_SKIP_IDS", "")) | _ids(os.getenv("LEARNING_SKIP_CHANNEL_IDS", ""))
try:
    qna = int(os.getenv("LEARNING_QNA_CHANNEL_ID", os.getenv("QNA_CHANNEL_ID", "0")) or "0")  # type: ignore
    if qna:
        SKIP.add(qna)
except Exception:
    pass

class ShadowLearningObserverOverlay(commands.Cog):
    """
    Observe user messages (non-bot) in non-QNA channels and award exposure XP.
    """
    def __init__(self, bot):
        self.bot = bot
        self._last: dict[int, float] = {}

    def _ok(self, uid: int) -> bool:
        now = time.time()
        last = self._last.get(uid, 0.0)
        if now - last < COOLDOWN:
            return False
        self._last[uid] = now
        return True

    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if not ENABLE:
            return
        if m.guild is None:
            return
        if getattr(m.author, "bot", False):
            return
        ch = getattr(m, "channel", None)
        ch_id = getattr(ch, "id", None)
        if ch_id and ch_id in SKIP:
            return
        if XP <= 0:
            return
        if not self._ok(getattr(m.author, "id", 0)):
            return
        # Dispatch XP events (compatible with multiple consumers)
        for evt in ("satpam_xp", "xp_add", "xp_award"):
            try:
                self.bot.dispatch(evt, m.author.id, XP, "shadow_exposure")
            except Exception:
                pass
        log.debug("[shadow-observer] +%s XP -> user=%s ch=%s", XP, getattr(m.author, "id", None), ch_id)

async def setup(bot):
    await bot.add_cog(ShadowLearningObserverOverlay(bot))
