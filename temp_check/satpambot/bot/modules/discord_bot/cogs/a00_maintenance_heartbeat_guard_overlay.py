
from __future__ import annotations
import os, time, logging

import discord
from discord.ext import commands

try:
    from satpambot.bot.modules.discord_bot.helpers.embed_scribe import EmbedScribe
except Exception:
    EmbedScribe = None

log = logging.getLogger(__name__)

def _intenv(k, d):
    try: return int(os.getenv(k, str(d)))
    except Exception: return d

def _strenv(k, d):
    v = os.getenv(k, d)
    return v if v is not None else d

class MaintenanceHeartbeatGuard(commands.Cog):
    """Throttle 'Maintenance / Heartbeat ok' messages so they don't spam.

    Behaviour:
      - If a Maintenance embed appears more than once within cooldown, delete the extra.
      - Optionally convert Maintenance posts into a single pinned message via EmbedScribe.upsert.

    ENV:
      MAINT_HEARTBEAT_COOLDOWN_SEC (default 600)
      MAINT_HEARTBEAT_USE_UPSERT   (default 1)  -> edit single pinned message
      MAINT_HEARTBEAT_MARKER       (default 'maintenance:heartbeat')
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cooldown = max(30, _intenv("MAINT_HEARTBEAT_COOLDOWN_SEC", 600))
        self.use_upsert = bool(_intenv("MAINT_HEARTBEAT_USE_UPSERT", 1))
        self.marker = _strenv("MAINT_HEARTBEAT_MARKER", "maintenance:heartbeat")
        self._last = {}  # channel_id -> (ts, last_mid)

    def _looks_like_maintenance(self, m: "discord.Message") -> bool:
        if not getattr(getattr(m, "author", None), "bot", False):
            return False
        if not getattr(m, "embeds", None):
            return False
        e = m.embeds[0]
        title = (getattr(e, "title", "") or "").strip().lower()
        if title == "maintenance":
            return True
        # safeguard: detect marker content to avoid loops
        c = (getattr(m, "content", "") or "").lower()
        if "maintenance" in c and "heartbeat" in c:
            return True
        return False

    @commands.Cog.listener()
    async def on_message(self, m: "discord.Message"):
        try:
            if not self._looks_like_maintenance(m):
                return
            # don't touch messages that already carry our marker (upsert result)
            content = (getattr(m, "content", "") or "")
            if self.marker and self.marker in content:
                return

            ch = m.channel
            now = time.time()
            last_ts, last_mid = self._last.get(ch.id, (0, None))
            if now - last_ts < self.cooldown:
                # within cooldown -> delete the new duplicate
                try:
                    await m.delete()
                    log.info("[maint-guard] deleted duplicate heartbeat in #%s", ch.id)
                except Exception:
                    pass
                return

            # first/new heartbeat within window
            if self.use_upsert and EmbedScribe is not None:
                try:
                    # Convert to a single pinned message that we update in-place
                    mid = await EmbedScribe.upsert(
                        self.bot, ch.id,
                        content=self.marker,
                        embed=m.embeds[0],
                        marker=self.marker,
                        pin=True,
                    )
                    self._last[ch.id] = (now, mid or m.id)
                    try:
                        await m.delete()
                    except Exception:
                        pass
                    return
                except Exception as e:
                    log.debug("[maint-guard] upsert failed; fallback keep message: %r", e)

            # fallback: just record timestamp; keep the message
            self._last[ch.id] = (now, m.id)
        except Exception as e:
            log.debug("[maint-guard] error: %r", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(MaintenanceHeartbeatGuard(bot))
