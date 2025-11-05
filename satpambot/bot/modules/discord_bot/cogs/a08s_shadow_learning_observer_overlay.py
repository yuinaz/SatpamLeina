from __future__ import annotations
import os, time, logging
from typing import Set, Dict, Optional
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

def _env_bool(k: str, default: bool=False) -> bool:
    v = os.getenv(k)
    if v is None or v == "":
        return default
    return str(v).lower() in ("1","true","yes","on")

def _parse_ids(raw: Optional[str]) -> Set[int]:
    out: Set[int] = set()
    for part in (raw or "").replace(";", ",").split(","):
        part = part.strip()
        if not part: 
            continue
        try:
            out.add(int(part))
        except Exception:
            pass
    return out

PER_EXPOSURE_XP = int(os.getenv("SHADOW_EXPOSURE_XP", "15") or "15")
USER_COOLDOWN_SEC = int(os.getenv("SHADOW_XP_COOLDOWN_SEC", "180") or "180")
ENABLE = _env_bool("SHADOW_ENABLE", True)

# Build skip-set (QNA channel is skipped otomatis)
SKIP_IDS: Set[int] = _parse_ids(os.getenv("SHADOW_SKIP_IDS")) | _parse_ids(os.getenv("LEARNING_SKIP_CHANNEL_IDS"))
try:
    _qna = int(os.getenv("LEARNING_QNA_CHANNEL_ID", os.getenv("QNA_CHANNEL_ID", "0")) or "0")
    if _qna:
        SKIP_IDS.add(_qna)
except Exception:
    pass

class ShadowLearningObserverOverlay(commands.Cog):
    """Award +15 XP per user exposure (cooldown per user), skip QNA & channels in SKIP_IDS.
    This file name follows the a08*_*_overlay pattern so loader will pick it up.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_award: Dict[int, float] = {}
        log.info("[shadow-observer] armed: enable=%s xp=%s cooldown=%ss skip=%s",
                 ENABLE, PER_EXPOSURE_XP, USER_COOLDOWN_SEC, sorted(SKIP_IDS) if SKIP_IDS else "-")

    def _cooldown_ok(self, uid: int) -> bool:
        now = time.time()
        last = self._last_award.get(uid, 0.0)
        if (now - last) < USER_COOLDOWN_SEC:
            return False
        self._last_award[uid] = now
        return True

    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if not ENABLE:
            return
        try:
            if m.guild is None or m.author.bot:
                return
            ch_id = getattr(getattr(m, "channel", None), "id", None)
            if ch_id and ch_id in SKIP_IDS:
                return

            if PER_EXPOSURE_XP > 0 and self._cooldown_ok(m.author.id):
                # Emit XP events for compatibility; prefer 'satpam_xp' if bridge listens to it.
                awarded = False
                for evt in ("satpam_xp", "xp_add", "xp_award"):
                    try:
                        self.bot.dispatch(evt, m.author.id, PER_EXPOSURE_XP, "shadow_exposure")
                        awarded = True
                    except Exception:
                        pass
                if awarded:
                    log.debug("[shadow-observer] +%s XP -> user=%s ch=%s reason=shadow_exposure",
                              PER_EXPOSURE_XP, m.author.id, ch_id)
        except Exception:
            log.exception("[shadow-observer] on_message error")

async def setup(bot: commands.Bot):
    await bot.add_cog(ShadowLearningObserverOverlay(bot))
