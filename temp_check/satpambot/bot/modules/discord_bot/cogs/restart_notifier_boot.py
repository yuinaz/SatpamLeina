
from discord.ext import commands
import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

import discord

log = logging.getLogger(__name__)


@dataclass
class RestartTicket:
    channel_id: Optional[int] = None
    message_id: Optional[int] = None
    author_id: Optional[int] = None
    started_at: Optional[str] = None  # ISO8601
    commit: Optional[str] = None

    @classmethod
    def load_any(cls) -> Tuple[Optional["RestartTicket"], Optional[Path]]:
        """Load a ticket from one of the supported paths, if any."""
        paths = [
            Path("/tmp/restart_ticket.json"),
            Path(".satpambot_restart_ticket.json"),
            Path("restart_ticket.json"),
        ]
        for p in paths:
            try:
                if p.exists():
                    data = json.loads(p.read_text(encoding="utf-8"))
                    # normalize keys: allow camelCase or snake_case
                    def g(k, *alts):
                        for key in (k, *alts):
                            if key in data:
                                return data[key]
                        return None
                    return (
                        cls(
                            channel_id=g("channel_id", "channelId"),
                            message_id=g("message_id", "messageId"),
                            author_id=g("author_id", "authorId"),
                            started_at=g("started_at", "startedAt"),
                            commit=g("commit", "sha", "short_sha"),
                        ),
                        p,
                    )
            except Exception:
                log.exception("[restart_notifier_boot] gagal baca ticket dari %s", p)
        return None, None


def _seconds_since_iso(ts: Optional[str]) -> Optional[int]:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int((datetime.now(timezone.utc) - dt).total_seconds())
    except Exception:
        return None


def _format_duration(sec: Optional[int]) -> str:
    if sec is None:
        return "?s"
    if sec < 60:
        return f"{sec}s"
    m, s = divmod(sec, 60)
    if m < 60:
        return f"{m}m{s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m{s:02d}s"


def _discover_log_channel(bot: commands.Bot) -> Optional[discord.TextChannel]:
    """Try to find a reasonable log channel without env/config dependencies."""
    # 1) Try env vars if present, but NOT required
    for key in ("LOG_CHANNEL_ID", "LOG_CHANNEL_ID_RAW", "LOG_CHANNEL"):
        val = None
        try:
            val = os.environ.get(key)
        except Exception:
            val = None
        if val:
            try:
                ch = bot.get_channel(int(val))
                if isinstance(ch, discord.TextChannel):
                    return ch
            except Exception:
                pass
    # 2) Fallback by name heuristics
    names = [
        "log-botphising",
        "log-botphishing",
        "errorlog-bot",
        "bot-logs",
        "logs",
    ]
    for g in bot.guilds:
        for ch in g.text_channels:
            try:
                if ch.name in names:
                    return ch
            except Exception:
                continue
    # last resort: first text channel of first guild
    for g in bot.guilds:
        for ch in g.text_channels:
            return ch
    return None


class RestartNotifierBoot(commands.Cog):
    """On boot, look for a restart ticket and edit the 'Restarting…' message.

    If the message can't be edited (e.g., ID changed or missing), send a new
    "✅ Restarted" confirmation into a discovered log channel. The ticket file
    is deleted once processed, so the action is idempotent across reconnects.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._done = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self._done:
            return
        self._done = True
        await self._handle_restart_notice()

    async def _handle_restart_notice(self):
        ticket, path = RestartTicket.load_any()
        if not ticket:
            log.info("[restart_notifier_boot] tidak ada restart ticket ditemukan")
            return

        elapsed = _seconds_since_iso(ticket.started_at)
        duration = _format_duration(elapsed)
        commit_str = f" • {ticket.commit}" if ticket.commit else ""
        content = f"✅ Restarted in {duration}{commit_str}"

        # Try edit the original message if IDs are present
        edited = False
        if ticket.channel_id and ticket.message_id:
            try:
                ch = self.bot.get_channel(int(ticket.channel_id)) or await self.bot.fetch_channel(int(ticket.channel_id))
                if isinstance(ch, (discord.TextChannel, discord.Thread)):
                    try:
                        msg = await ch.fetch_message(int(ticket.message_id))
                        await msg.edit(content=content)
                        edited = True
                        log.info("[restart_notifier_boot] edited restart message in #%s", getattr(ch, 'name', ch.id))
                    except discord.NotFound:
                        log.warning("[restart_notifier_boot] restart message not found; will send new message")
                    except Exception:
                        log.exception("[restart_notifier_boot] gagal edit pesan restart")
            except Exception:
                log.exception("[restart_notifier_boot] gagal akses channel/message untuk edit")

        # If we couldn't edit, post a fresh one in a log channel
        if not edited:
            try:
                ch = _discover_log_channel(self.bot)
                if ch is not None:
                    await ch.send(content)
                    log.info("[restart_notifier_boot] posted new restart message in #%s", getattr(ch, 'name', ch.id))
                else:
                    log.warning("[restart_notifier_boot] tidak menemukan channel untuk kirim notifikasi restart")
            except Exception:
                log.exception("[restart_notifier_boot] gagal kirim notifikasi restart baru")

        # Clean up the ticket
        try:
            if path and path.exists():
                path.unlink(missing_ok=True)
        except Exception:
            log.exception("[restart_notifier_boot] gagal hapus ticket %s", path)
async def setup(bot: commands.Bot):
    await bot.add_cog(RestartNotifierBoot(bot))