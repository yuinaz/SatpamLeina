from __future__ import annotations
from discord.ext import commands

# from __future__ import annotations
"""
a08_xp_message_awarder_overlay.py
---------------------------------
Drop-in overlay to *force-enable* XP awarding per user message, with cooldown.
Tries multiple backends: XPDiscordBackend, XPCommand, or event dispatch.
Safe for smoke import: only installs listeners; no slash commands; no external deps.
"""


import asyncio
import logging
import time
import os
from typing import Optional, Dict

import discord

log = logging.getLogger(__name__)

# ==== CONFIG (edit here if needed) =========================================
# Default per-message XP; prefer environment override for flexibility
PER_MESSAGE_XP: int = int(os.getenv("PER_MESSAGE_XP", "15"))  # consistent +15 XP per message
USER_COOLDOWN_SEC: int = int(os.getenv("USER_COOLDOWN_SEC", "45"))  # per-user cooldown
CHANNEL_ALLOWLIST: Optional[set[int]] = None  # e.g., {1234567890123, 2345678901234}, or None for all guild text chans
IGNORE_BOTS: bool = True                 # ignore bot & webhook messages
# ==========================================================================

class _XPBackendFacade:
    """Facade that tries to talk to any XP backend we can find."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._resolved = False
        self._method = None
        self._owner = None  # which cog holds the method
        self._tried = False

    def _resolve(self) -> None:
        if self._resolved or self._tried:
            return
        self._tried = True

        candidates = [self.bot.get_cog("XPDiscordBackend"), self.bot.get_cog("XPCommand")]
        method_names = ["add_xp", "award_xp", "add", "award", "give"]

        for owner in [c for c in candidates if c]:
            for name in method_names:
                fn = getattr(owner, name, None)
                if callable(fn):
                    self._method = fn
                    self._owner = owner
                    self._resolved = True
                    log.info("[xp-awarder] Using method %s.%s for XP award", type(owner).__name__, name)
                    return

        # fall back: use event dispatch (may or may not be handled)
        self._method = None
        self._owner = None
        self._resolved = True
        log.warning("[xp-awarder] No direct XP method found. Will dispatch events: 'xp_add', 'xp.award', 'satpam_xp'.")

    async def award(self, user: discord.abc.User, amount: int, reason: str) -> bool:
        self._resolve()
        if self._method:
            try:
                res = self._method(user, amount, reason)  # try (user, amount, reason)
            except TypeError:
                try:
                    res = self._method(user.id, amount, reason)  # try (user_id, amount, reason)
                except TypeError:
                    try:
                        res = self._method(user, amount)  # try (user, amount)
                    except TypeError:
                        try:
                            res = self._method(user.id, amount)  # try (user_id, amount)
                        except TypeError as e:
                            log.error("[xp-awarder] XP method signature not recognized: %r", e)
                            return False

            if asyncio.iscoroutine(res):
                await res
            return True

        # Dispatch events for compatibility
        try:
            self.bot.dispatch("xp_add", user, amount, reason)
            self.bot.dispatch("xp.award", user, amount, reason)
            self.bot.dispatch("satpam_xp", user, amount, reason)
            return True  # we can't verify if listeners exist, but we did our part
        except Exception as e:
            log.exception("[xp-awarder] failed to dispatch xp events: %r", e)
            return False


class XPOnMessageOverlay(commands.Cog):
    """Award PER_MESSAGE_XP on eligible messages with per-user cooldown."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.backend = _XPBackendFacade(bot)
        self._last_award: Dict[int, float] = {}  # user_id -> last_ts

    def _eligible(self, message: discord.Message) -> bool:
        if message.guild is None:
            return False  # skip DMs
        if IGNORE_BOTS and (message.author.bot or message.webhook_id is not None):
            return False
        if not isinstance(message.channel, (discord.TextChannel, discord.Thread)):
            return False
        if CHANNEL_ALLOWLIST is not None:
            ch_id = message.channel.id if isinstance(message.channel, discord.TextChannel) else message.channel.parent_id or message.channel.id
            if ch_id not in CHANNEL_ALLOWLIST:
                return False
        return True

    @commands.Cog.listener("on_message")
    async def on_message_award_xp(self, message: discord.Message):
        try:
            if not self._eligible(message):
                return
            now = time.monotonic()
            last = self._last_award.get(message.author.id, 0.0)
            if (now - last) < USER_COOLDOWN_SEC:
                return

            ok = await self.backend.award(message.author, PER_MESSAGE_XP, reason="chat:message")
            if ok:
                self._last_award[message.author.id] = now
                log.debug("[xp-awarder] +%s XP to %s", PER_MESSAGE_XP, message.author)
            else:
                log.warning("[xp-awarder] backend returned False for %s", message.author)
        except Exception:
            log.exception("[xp-awarder] error during on_message handling")

async def setup(bot: commands.Bot):
    await bot.add_cog(XPOnMessageOverlay(bot))
    log.info("[xp-awarder] overlay loaded: on_message -> XP +%s / %ss cooldown", PER_MESSAGE_XP, USER_COOLDOWN_SEC)