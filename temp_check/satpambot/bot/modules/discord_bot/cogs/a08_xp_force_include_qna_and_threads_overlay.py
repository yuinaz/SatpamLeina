from discord.ext import commands
from discord import Message, Member, User
from typing import Union, Optional

# --- PATCH: robust fallback that does not import XPStore class ---
import logging as _logging
_log = _logging.getLogger(__name__)
async def _award_via_event(bot: commands.Bot, author: Union[Member, User], amount: int, message: Optional[Message] = None, reason: str = "qna/thread"):
    try:
        guild_id = getattr(getattr(message, "guild", None), "id", None) if message else None
        channel_id = getattr(getattr(message, "channel", None), "id", None) if message else None
        message_id = getattr(message, "id", None) if message else None
        bot.dispatch("xp_add",
            user_id=getattr(author, "id", None),
            amount=int(amount),
            guild_id=guild_id, channel_id=channel_id, message_id=message_id,
            reason=reason,
        )
        return True
    except Exception as e:
        _log.exception("[xp_force] event dispatch failed: %r", e)
        return False

import logging
import os
import time
from typing import Optional, Dict, Any, Type, cast, Protocol, TypedDict, runtime_checkable, Final

log = logging.getLogger(__name__)

class UserData(TypedDict):
    """User data in XP store"""
    xp: int

class XPStoreData(TypedDict):
    """XP store data structure"""
    users: Dict[str, UserData]

# Define XPStore protocol for type hints
@runtime_checkable
class XPStoreProtocol(Protocol):
    """Protocol for XP store operations"""
    @staticmethod
    def load() -> Any: ...  # Return Any to avoid type conflicts
    @staticmethod
    def save(data: Any) -> None: ...  # Accept Any to avoid type conflicts

from typing import Any as _Any
try:
    from satpambot.bot.modules.discord_bot.services.xp_store import XPStore as _XPStoreImpl  # type: ignore
    XPStore: _Any = cast(_Any, _XPStoreImpl)
except Exception:
    XPStore: _Any = None  # type: ignore

# Default user data
EMPTY_USER_DATA: Final[Dict[str, int]] = {"xp": 0}

FORCE_INCLUDE_QNA = True
COOLDOWN_SEC = 6

class XPForceIncludeOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last: dict[int, float] = {}  # author_id -> ts

    def _allowed(self, message: Message) -> bool:
        # Always include threads
        if getattr(message.channel, "type", None) and str(message.channel.type).endswith("thread"):
            return True
        # Include QNA if configured overlay is present
        if FORCE_INCLUDE_QNA:
            name = getattr(message.channel, "name", "") or ""
            if "qna" in name.lower():
                return True
        return False

    def _cool(self, author_id: int) -> bool:
        now = time.time()
        last = self._last.get(author_id, 0.0)
        if now - last >= COOLDOWN_SEC:
            self._last[author_id] = now
            return True
        return False

    @commands.Cog.listener("on_message")
    async def on_message(self, message: Message) -> None:
        try:
            if message.author.bot:
                return
            if not self._allowed(message):
                return
            if not self._cool(message.author.id):
                return

            # Prefer direct award events; else fallback to XPStore file/upstash via compat overlay
            dispatched = 0
            # use configured per-message XP (fall back to normalizer target env or 15)
            amt = int(os.getenv("PER_MESSAGE_XP", os.getenv("XP_NORMALIZER_TARGET_PER_MESSAGE", "15")))
            for evt in ("xp_add", "xp.award", "satpam_xp"):
                try:
                    self.bot.dispatch(evt, message.author.id, amt, reason="force-include")
                    dispatched += 1
                except Exception:
                    pass

            if dispatched == 0 and XPStore is not None and all(hasattr(XPStore, attr) for attr in ["load", "save"]):
                try:
                    # Load and validate store data
                    data = XPStore.load()  # type: ignore
                    if not isinstance(data, dict):
                        raise TypeError("XPStore.load() must return a dict")
                    
                    # Ensure users dict exists
                    if "users" not in data or not isinstance(data["users"], dict):
                        data["users"] = {}
                    users = data["users"]  # type: ignore
                    
                    # Handle user data update
                    user_id = str(message.author.id)
                    if user_id not in users or not isinstance(users[user_id], dict):
                        users[user_id] = EMPTY_USER_DATA.copy()
                    
                    try:
                        # Safe XP update with validation
                        current_xp = int(users[user_id].get("xp", 0))  # type: ignore
                        users[user_id]["xp"] = current_xp + amt  # type: ignore
                        XPStore.save(data)  # type: ignore
                        log.info("[xp_force] fallback awarded +%s via XPStore (uid=%s)", amt, user_id)
                    except (ValueError, TypeError, KeyError) as e:
                        log.warning("[xp_force] XP update failed: %s", e)
                    log.info("[xp_force] fallback awarded +%s via XPStore compat (uid=%s)", amt, message.author.id)
                except Exception as e:
                    log.warning("[xp_force] XPStore fallback failed: %s", e)
            else:
                log.debug("[xp_force] dispatched award events=%d (uid=%s)", dispatched, message.author.id)
        except Exception as e:
            log.warning("[xp_force] error: %s", e)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(XPForceIncludeOverlay(bot))