from __future__ import annotations
import os, logging, asyncio
from typing import Optional, Tuple
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

MARKERS = ("leina:curriculum", "curriculum_progress", "leina:progress")
DEFAULT_TITLE_HINTS = ("Curriculum", "Leina Curriculum", "Progress Kurikulum")

def _env_int(key: str, default: Optional[int]=None) -> Optional[int]:
    v = os.getenv(key, None)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return default

class CurriculumAutoPin(commands.Cog):
    """
    Make sure the curriculum progress message is pinned.
    No import-time side effects; resilient if config functions are absent.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task: Optional[asyncio.Task] = None

    @commands.Cog.listener()
    async def on_ready(self):
        if self._task is None:
            self._task = asyncio.create_task(self._bootstrap(), name="curriculum_autopin_bootstrap")

    async def _bootstrap(self):
        await self.bot.wait_until_ready()
        try:
            cid, mid = await self._load_target()
            if not cid:
                log.warning("[curriculum_autopin] no channel id resolved")
                return
            ch = self.bot.get_channel(cid)  # type: ignore
            if ch is None:
                ch = await self.bot.fetch_channel(cid)  # type: ignore

            # If we already know a message id, pin it
            if mid:
                try:
                    m = await ch.fetch_message(mid)  # type: ignore
                    await self._pin(m)
                    log.info("[curriculum_autopin] pinned by id: %s", mid)
                    return
                except Exception as e:
                    log.warning("[curriculum_autopin] fetch by id failed: %r", e)

            # Try find by markers in pinned messages
            try:
                pins = await ch.pins()  # type: ignore
                for m in pins:
                    if self._is_candidate(m):
                        await self._pin(m)
                        log.info("[curriculum_autopin] ensured existing pin (found in pins)")
                        return
            except Exception as e:
                log.debug("[curriculum_autopin] pins scan failed: %r", e)

            # Try find in recent history
            try:
                async for m in ch.history(limit=50):  # type: ignore
                    if self._is_candidate(m):
                        await self._pin(m)
                        log.info("[curriculum_autopin] pinned found message from history")
                        return
            except Exception as e:
                log.debug("[curriculum_autopin] history scan failed: %r", e)

            # Fallback: create a placeholder marker message and pin it
            try:
                marker = MARKERS[0]
                m = await ch.send(marker)  # type: ignore
                await self._pin(m)
                log.info("[curriculum_autopin] created placeholder and pinned (msg_id=%s)", m.id)
            except Exception as e:
                log.warning("[curriculum_autopin] create placeholder failed: %r", e)
        except Exception as e:
            log.exception("[curriculum_autopin] bootstrap failed: %r", e)

    async def _pin(self, m: discord.Message):
        try:
            await m.pin()
        except Exception:
            pass  # it's fine if already pinned

    def _is_candidate(self, m: discord.Message) -> bool:
        try:
            content = (m.content or "").lower()
            if any(k in content for k in (k.lower() for k in MARKERS)):
                return True
            # check embed title hints
            for e in (m.embeds or []):
                title = (e.title or "").lower()
                if any(h.lower() in title for h in DEFAULT_TITLE_HINTS):
                    return True
        except Exception:
            pass
        return False

    async def _load_target(self) -> Tuple[Optional[int], Optional[int]]:
        """
        Resolve (channel_id, message_id) from multiple sources:
         - a20_curriculum_tk_sd._load_cfg() if available
         - ENV: CURRICULUM_CHANNEL_ID / CURRICULUM_MESSAGE_ID
         - Fallback to KV_JSON_CHANNEL_ID / LEINA_XP_STATUS_CHANNEL_ID (same log thread)
        """
        # 1) Try a20 module helper if present
        try:
            from satpambot.bot.modules.discord_bot.cogs import a20_curriculum_tk_sd as a20
            fn = getattr(a20, "_load_cfg", None)
            if callable(fn):
                cfg = fn()
                cid = cfg.get("report_channel_id") or cfg.get("channel_id")
                mid = cfg.get("report_message_id") or cfg.get("message_id")
                if cid:
                    return int(cid), (int(mid) if mid else None)
        except Exception as e:
            # Just warn; we will fallback to ENV
            log.debug("[curriculum_autopin] a20._load_cfg not available: %r", e)

        # 2) ENV
        cid = _env_int("CURRICULUM_CHANNEL_ID", None)
        mid = _env_int("CURRICULUM_MESSAGE_ID", None)
        if cid:
            return cid, mid

        # 3) Fallback to commonly used channels (KV/XP status channel)
        cid = _env_int("KV_JSON_CHANNEL_ID", None) or _env_int("LEINA_XP_STATUS_CHANNEL_ID", None)
        return cid, None

async def setup(bot: commands.Bot):
    await bot.add_cog(CurriculumAutoPin(bot))
    log.info("[curriculum_autopin] loaded")
