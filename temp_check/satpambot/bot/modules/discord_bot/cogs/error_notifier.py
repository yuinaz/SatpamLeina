
from discord.ext import commands
\
# satpambot/bot/modules/discord_bot/cogs/error_notifier.py
import os
import time
import traceback
import logging
from typing import Dict

import aiohttp
from discord.ext import tasks
import discord

log = logging.getLogger(__name__)

LOG_CHANNEL_ID = int(os.environ.get("DISCORD_LOG_CHANNEL_ID", "0") or "0")
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()

# Simple in-process throttle memory
_LAST_SEND: Dict[str, float] = {}

def _throttle(key: str, sec: int = 120) -> bool:
    """Return True if we should SKIP sending (i.e., throttled)."""
    now = time.time()
    last = _LAST_SEND.get(key, 0)
    if last + sec > now:
        return True
    _LAST_SEND[key] = now
    return False

async def _send_webhook(text: str):
    if not WEBHOOK_URL:
        return
    try:
        async with aiohttp.ClientSession() as sess:
            await sess.post(WEBHOOK_URL, json={"content": text[:1900]})
    except Exception as e:
        log.warning("webhook send failed: %r", e)

async def _send_channel(bot: commands.Bot, text: str):
    if not LOG_CHANNEL_ID:
        return
    try:
        ch = bot.get_channel(LOG_CHANNEL_ID)
        if ch is None:
            ch = await bot.fetch_channel(LOG_CHANNEL_ID)
        if isinstance(ch, (discord.TextChannel, discord.Thread)):
            await ch.send(text[:1900])
    except Exception as e:
        log.warning("channel send failed: %r", e)

def _fmt_exc(prefix: str, exc: BaseException) -> str:
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    # keep tail to avoid huge spam
    return f"{prefix}\n```\n{tb[-1800:]}\n```"

class ErrorNotifier(commands.Cog):
    """Minimal notifier anti-spam.
    - NO health/uptime spam.
    - Heartbeat OFF by default (only if env set).
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.heartbeat.start()

    def cog_unload(self):
        self.heartbeat.cancel()

    @tasks.loop(minutes=10.0)
    async def heartbeat(self):
        """Heartbeat ringan setiap 10 menit (hanya jika env diset)."""
        if not (LOG_CHANNEL_ID or WEBHOOK_URL):
            return
        if _throttle("heartbeat", 600):  # 10 menit throttle
            return
        try:
            if self.bot.is_ready():
                text = f"✅ Heartbeat OK | guilds={len(self.bot.guilds)} | latency={getattr(self.bot, 'latency', 0):.3f}s"
                await _send_channel(self.bot, text)
                await _send_webhook(text)
        except Exception as e:
            log.warning("heartbeat failed: %r", e)

    @heartbeat.before_loop
    async def before_heartbeat(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_error(self, event_method, *args, **kwargs):
        key = f"on_error:{event_method}"
        if _throttle(key, 120):
            return
        text = f"⚠️ on_error in `{event_method}`"
        await _send_channel(self.bot, text)
        await _send_webhook(text)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        # Skip CommandNotFound (non-MOD typing '!')
        if isinstance(error, commands.CommandNotFound):
            return
        key = f"cmd:{type(error).__name__}"
        if _throttle(key, 120):
            return
        text = _fmt_exc("❗ Command error", error)
        await _send_channel(self.bot, text)
        await _send_webhook(text)

    @commands.Cog.listener()
    async def on_disconnect(self):
        if _throttle("on_disconnect", 120):
            return
        await _send_channel(self.bot, "🔌 Bot disconnected")
        await _send_webhook("🔌 Bot disconnected")

    @commands.Cog.listener()
    async def on_resumed(self):
        if _throttle("on_resumed", 120):
            return
        await _send_channel(self.bot, "🔁 Bot resumed")
        await _send_webhook("🔁 Bot resumed")
async def setup(bot: commands.Bot):
    await bot.add_cog(ErrorNotifier(bot))