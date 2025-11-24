from __future__ import annotations

from discord.ext import commands

import logging, os
from typing import Iterable, Set
import discord

from urllib.parse import urlparse

try:
    import aiohttp
except Exception:
    aiohttp = None  # type: ignore

from ..helpers.safety_utils import extract_urls, norm_domain, is_suspicious_domain, SHORTENERS

log = logging.getLogger(__name__)

def _allowlist() -> Set[str]:
    raw = os.getenv("LINK_WHITELIST","")
    allow: Set[str] = set()
    for part in raw.split(","):
        p = part.strip().lower()
        if p:
            allow.add(p)
    allow.update({"discord.com","discord.gg"})
    return allow

ENABLED = os.getenv("LINK_GUARD_ENABLED","1") not in {"0","false","no"}
ACTION = os.getenv("LINK_GUARD_ACTION","delete").lower()  # delete|ban|log (respect env)
RESOLVE = os.getenv("URL_RESOLVE_ENABLED","false").lower() in {"1","true","yes"}
AUTOBAN_CRITICAL = os.getenv("URL_AUTOBAN_CRITICAL","0").lower() in {"1","true","yes"}
HEAD_TIMEOUT = float(os.getenv("HEAD_TIMEOUT","3.0"))
MAX_REDIRECTS = int(os.getenv("MAX_REDIRECTS","2"))

class LinkGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _expand_once(self, url: str) -> str:
        if not RESOLVE or aiohttp is None:
            return url
        host = norm_domain(urlparse(url).hostname or "")
        if host not in SHORTENERS:
            return url
        try:
            timeout = aiohttp.ClientTimeout(total=HEAD_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as sess:
                async with sess.head(url, allow_redirects=False) as resp:
                    loc = resp.headers.get("Location")
                    if loc and loc.startswith("http"):
                        return loc
        except Exception:
            return url
        return url

    async def _expand(self, url: str) -> str:
        out = url
        for _ in range(MAX_REDIRECTS):
            nxt = await self._expand_once(out)
            if nxt == out:
                break
            out = nxt
        return out

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # --- PublicChatGate pre-send guard (auto-injected) ---
        gate = None
        try:
            gate = self.bot.get_cog("PublicChatGate")
        except Exception:
            pass
        try:
            if message.guild and gate and hasattr(gate, "should_allow_public_reply") and not gate.should_allow_public_reply(message):
                return
        except Exception:
            pass
        # --- end guard ---

        # THREAD/FORUM EXEMPTION — auto-inserted
        ch = getattr(message, "channel", None)
        if ch is not None:
            try:
                import discord
                # Exempt true Thread objects
                if isinstance(ch, getattr(discord, "Thread", tuple())):
                    return
                # Exempt thread-like channel types (public/private/news threads)
                ctype = getattr(ch, "type", None)
                if ctype in {
                    getattr(discord.ChannelType, "public_thread", None),
                    getattr(discord.ChannelType, "private_thread", None),
                    getattr(discord.ChannelType, "news_thread", None),
                }:
                    return
            except Exception:
                # If discord import/type checks fail, do not block normal flow
                pass
        if not ENABLED or message.author.bot or not message.guild:
            return
        urls = extract_urls(message.content or "")
        if not urls:
            return
        allow = _allowlist()
        hits = []
        for u in urls:
            eu = await self._expand(u)
            host = norm_domain(urlparse(eu).hostname or "")
            if is_suspicious_domain(host, allow):
                hits.append((eu, host))
        if hits:
            try:
                if ACTION in {"delete","ban"}:
                    await message.delete()
            except Exception:
                pass
            if (ACTION == "ban" or AUTOBAN_CRITICAL) and hits:
                # only ban if env requests it; otherwise delete/log only
                from ..helpers.ban_utils import safe_ban_7d
                await safe_ban_7d(message.guild, message.author, reason=f"Suspicious link: {hits[:3]}")
            log.info("[link_guard] action=%s user=%s hits=%s", ACTION.upper(), message.author.id, hits[:5])