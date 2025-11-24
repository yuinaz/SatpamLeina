from __future__ import annotations

from discord.ext import commands

import os, asyncio, logging, re
from typing import Iterable, Set

import discord

from ._idempotent import set_once_flag, TTLSet, LogCoalescer

log = logging.getLogger(__name__)

def _split_csv(env: str) -> Set[int]:
    raw = os.getenv(env, "") or ""
    out: Set[int] = set()
    for p in raw.replace(";", ",").split(","):
        p = p.strip()
        if not p:
            continue
        try:
            out.add(int(p))
        except ValueError:
            pass
    return out

def _name_match_any(name: str, needles: Iterable[str]) -> bool:
    name = (name or "").lower()
    for n in needles:
        n = (n or "").strip().lower()
        if not n:
            continue
        if n in name:
            return True
    return False

class ChatNeuroLiteGuard(commands.Cog):
    """
    Keep neuro-lite progress channels clean from accidental bot public replies.
    Idempotent + log coalescing to avoid duplicate lines.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._ready_once = False
        self._seen = TTLSet(ttl_seconds=600.0, maxlen=4096)
        self._coalesce = LogCoalescer(
            emit_fn=lambda s: log.info("[chat_neurolite_guard] %s", s),
            delay=2.0,
            singular="deleted 1 bot public reply in neuro-lite progress",
            plural="deleted {n} bot public replies in neuro-lite progress (coalesced)",
        )
        self._task_boot = None

        self._enable = os.getenv("CHAT_NEUROLITE_GUARD_ENABLE", "1") not in ("0","false","no","off")
        needles = os.getenv("CHAT_NEUROLITE_GUARD_NAME_NEEDLES", "neuro-lite|progress")
        self._needles = [p.strip() for p in re.split(r"[|,;]", needles) if p.strip()]
        self._whitelist_ids = _split_csv("CHAT_NEUROLITE_GUARD_WHITELIST_IDS")

    async def cog_load(self) -> None:
        if not set_once_flag(self.bot, "_chat_neurolite_guard_loaded"):
            log.debug("[chat_neurolite_guard] already loaded; skip repeated setup")
            return
        if not self._enable:
            log.info("[chat_neurolite_guard] disabled by env")
            return
        self._task_boot = asyncio.create_task(self._bootstrap_once(), name="cng_boot")

    async def cog_unload(self) -> None:
        try:
            if self._task_boot:
                self._task_boot.cancel()
        except Exception:
            pass

    async def _bootstrap_once(self) -> None:
        await self.bot.wait_until_ready()
        if self._ready_once:
            return
        self._ready_once = True
        log.info("[chat_neurolite_guard] ready (idempotent=on, coalesce=on)")

    def _should_delete(self, m: discord.Message) -> bool:
        if not self._enable:
            return False
        try:
            if m.author.id != self.bot.user.id:
                return False
        except Exception:
            return False
        if m.guild is None:
            return False
        if self._whitelist_ids and m.channel.id in self._whitelist_ids:
            return False
        ch_name = getattr(m.channel, "name", "") or ""
        if not self._needles or _name_match_any(ch_name, self._needles):
            return True
        return False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self._enable:
            return
        if not self._should_delete(message):
            return
        if message.id in self._seen:
            return
        self._seen.add(message.id)
        try:
            await message.delete()
            await self._coalesce.bump()
        except discord.Forbidden:
            log.warning("[chat_neurolite_guard] missing permission to delete in #%s", getattr(message.channel, "name", "?"))
        except Exception as e:
            log.exception("[chat_neurolite_guard] delete failed: %r", e)
async def setup(bot: commands.Bot):
    if bot.get_cog("ChatNeuroLiteGuard"):
        return
    await bot.add_cog(ChatNeuroLiteGuard(bot))