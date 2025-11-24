from __future__ import annotations

from discord.ext import commands

import logging, os, asyncio, time, re
from typing import Optional, Iterable, Tuple, Set
import discord

from ..helpers.hash_utils import sha256_bytes
from ..helpers.safety_utils import extract_urls, norm_domain, is_suspicious_domain
from ..helpers.ban_utils import safe_ban_7d
from ..helpers.ocr_clients import smart_ocr

log = logging.getLogger(__name__)

# ENV
OCR_ENABLED = os.getenv("OCR_ENABLED","1").lower() in {"1","true","yes"}
OCR_ACTION = os.getenv("OCR_ACTION","delete").lower()   # delete|ban|log
OCR_RATE_PER_USER_SEC = float(os.getenv("OCR_RATE_PER_USER_SEC","30"))
OCR_SCAM_STRICT = os.getenv("OCR_SCAM_STRICT","0").lower() in {"1","true","yes"}  # if true, treat keyword hits as critical
OCR_SCORE_THRESHOLD = float(os.getenv("OCR_SCORE_THRESHOLD","0.0"))  # placeholder to match format

# Soft NSFW policy (ENV names provided by user)
SOFT_POLICY = os.getenv("NSFW_SOFT_POLICY","allow").lower()  # allow|delete|log (never ban)
SOFT_WORDS = {w.strip().lower() for w in (os.getenv("NSFW_SOFT_KEYWORDS","nsfw,18+,r18,lewd").split(",")) if w.strip()}
SOFT_TIMEOUT_MIN = int(os.getenv("NSFW_SOFT_TIMEOUT_MIN","0"))  # reserved / format keep
SOFT_THRESHOLD = float(os.getenv("NSFW_SOFT_THRESHOLD","0"))    # reserved / format keep

INVITE_RE = re.compile(r'(?:discord(?:\.gg|\.com/invite)/)([a-zA-Z0-9-]+)', re.I)
PHISH_WORDS = re.compile(r'(nitro|airdrop|bonus|free|verify|steam|robux|wallet|crypto)', re.I)

CACHE_TTL = 86400
MAX_BYTES = 1572864
_last_user: dict[int, float] = {}
_seen: dict[str, float] = {}

class OCRGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.enabled = OCR_ENABLED

    def _rate(self, uid: int) -> bool:
        now = time.time()
        last = _last_user.get(uid, 0.0)
        if now - last < OCR_RATE_PER_USER_SEC:
            return False
        _last_user[uid] = now
        return True

    def _dedupe(self, h: str) -> bool:
        now = time.time()
        ts = _seen.get(h, 0.0)
        if ts and (now - ts) < CACHE_TTL:
            return True
        _seen[h] = now
        return False

    async def _handle_invites(self, message: discord.Message, text: str) -> bool:
        codes = [m.group(1) for m in INVITE_RE.finditer(text or "")]
        if not codes:
            return False
        # fetch nsfw_level per code; ban only if nsfw
        for code in codes:
            try:
                inv = await self.bot.fetch_invite(code, with_counts=False)
            except Exception:
                inv = None
            if not inv or not inv.guild:
                # strict handling -> delete only
                if OCR_ACTION in {"delete","ban"}:
                    try: await message.delete()
                    except Exception: pass
                return True
            nsfw_level = getattr(inv.guild, "nsfw_level", -1) or -1
            if nsfw_level >= 2 and OCR_ACTION == "ban":
                try: await message.delete()
                except Exception: pass
                await safe_ban_7d(message.guild, message.author, reason=f"OCR NSFW invite (nsfw_level={nsfw_level})")
                return True
            else:
                if OCR_ACTION in {"delete","ban"}:
                    try: await message.delete()
                    except Exception: pass
                return True
        return False

    def _is_soft_only(self, text: str) -> bool:
        low = (text or "").lower()
        if not low:
            return False
        if INVITE_RE.search(low): 
            return False
        if PHISH_WORDS.search(low): 
            return False
        if extract_urls(low): 
            return False
        return any(w in low for w in SOFT_WORDS)

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
        if not self.enabled or message.author.bot or not message.attachments:
            return
        if not self._rate(message.author.id):
            return
        allow = {x.strip().lower() for x in (os.getenv("LINK_WHITELIST","").split(",")) if x.strip()}

        for att in message.attachments:
            if not getattr(att, "content_type","").startswith("image/"):
                continue
            if att.size > MAX_BYTES:
                continue
            try:
                b = await att.read()
            except Exception:
                continue
            h = sha256_bytes(b)
            if self._dedupe(h):
                continue
            txt = await smart_ocr(b, filename=att.filename or "image.jpg")
            if not txt:
                continue

            # 1) invites in image
            if await self._handle_invites(message, txt):
                return

            # 2) soft-NSFW policy
            if self._is_soft_only(txt):
                if SOFT_POLICY == "delete":
                    try: await message.delete()
                    except Exception: pass
                # allow/log otherwise (never ban for soft)
                return

            # 3) non-invite phishing indicators => apply OCR_ACTION but never ban for soft-only
            risky = bool(PHISH_WORDS.search(txt))
            if not risky:
                urls = extract_urls(txt)
                for u in urls:
                    try:
                        from urllib.parse import urlparse
                        host = norm_domain(urlparse(u).hostname or "")
                    except Exception:
                        host = ""
                    if is_suspicious_domain(host, allow):
                        risky = True; break
            if risky:
                if OCR_ACTION in {"delete","ban"}:
                    try: await message.delete()
                    except Exception: pass
                if OCR_ACTION == "ban" and OCR_SCAM_STRICT:
                    await safe_ban_7d(message.guild, message.author, reason="OCR suspicious content")
                return