from discord.ext import commands
import os
import asyncio
import logging
from datetime import datetime, timezone

import discord
from discord.ext import tasks

log = logging.getLogger(__name__)

TTL = int(os.getenv("LOG_AUTODELETE_TTL", "10"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))

# marker yang harus selamat
KEEP_MARKERS = (
    "SATPAMBOT_PINNED_MEMORY",
    "satpambot:auto_prune_state",
    "SATPAMBOT_KEEPER",
    "session-scope",
)

class AutoCleanLogChannel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ttl = TTL
        self.session_started_at = datetime.now(timezone.utc)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.loop.is_running():
            self.loop.start()
            log.info("[log_autodelete_focus] ready (ttl=%ss)", self.ttl)

    def _should_delete(self, m: discord.Message) -> bool:
        """SYNC predicate, supaya tidak ada 'was never awaited'."""
        try:
            # channel target saja
            if LOG_CHANNEL_ID and getattr(m.channel, "id", None) != LOG_CHANNEL_ID:
                return False
            # jangan hapus pinned
            if getattr(m, "pinned", False):
                return False
            # jangan hapus pesan sebelum session ini (pre-session)
            if getattr(m, "created_at", None) and m.created_at < self.session_started_at:
                return False
            # TTL belum lewat
            now = datetime.now(timezone.utc)
            created = getattr(m, "created_at", None) or now
            age = (now - created).total_seconds()
            if age < self.ttl:
                return False
            # keeper markers di content/embeds
            content = (getattr(m, "content", None) or "")
            if any(k in content for k in KEEP_MARKERS):
                return False
            for e in getattr(m, "embeds", []) or []:
                title = getattr(e, "title", None) or ""
                desc = getattr(e, "description", None) or ""
                if any(k in title or k in desc for k in KEEP_MARKERS):
                    return False
                for f in getattr(e, "fields", []) or []:
                    name = getattr(f, "name", None) or ""
                    value = getattr(f, "value", None) or ""
                    if any(k in name or k in value for k in KEEP_MARKERS):
                        return False
            return True
        except Exception:
            # kalau ada error parsing, jangan hapus
            log.exception("[log_autodelete_focus] check error; skip message")
            return False

    @tasks.loop(seconds=5)
    async def loop(self):
        if not LOG_CHANNEL_ID:
            return
        ch = self.bot.get_channel(LOG_CHANNEL_ID)
        if ch is None:
            try:
                ch = await self.bot.fetch_channel(LOG_CHANNEL_ID)
            except Exception:
                return

        # scan ringan; tidak gunakan purge(check=...) untuk hindari warning sync/async
        async for m in ch.history(limit=100, oldest_first=False):
            if self._should_delete(m):
                try:
                    await m.delete()
                    await asyncio.sleep(0.3)  # throttle
                except discord.NotFound:
                    pass  # sudah hilang
                except discord.Forbidden:
                    log.warning("[log_autodelete_focus] missing permission to delete in #%s", getattr(ch, "name", ch.id))
                    return
                except Exception:
                    log.exception("[log_autodelete_focus] delete failed")

    @loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()
async def setup(bot: commands.Bot):
    # v2 style: setup async + wajib di-await
    await bot.add_cog(AutoCleanLogChannel(bot))