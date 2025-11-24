from __future__ import annotations

import asyncio, json, os, time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import discord

NOTICE_PATH = Path(os.getenv("DATA_DIR", "data")) / "restart_notice.json"
LOG_CH_ID = int(os.getenv("PHASH_LOG_CHANNEL_ID", "0") or 0)

def _short_commit() -> str:
    # Try common envs Render/GitHub
    for k in ("RENDER_GIT_COMMIT", "GIT_COMMIT", "COMMIT_SHA"):
        v = os.getenv(k)
        if v:
            return v[:7]
    # Fallback: optional file written by your build (data/commit.txt)
    try:
        p = Path("data/commit.txt")
        if p.exists():
            return p.read_text(encoding="utf-8").strip()[:7]
    except Exception:
        pass
    return "unknown"

@dataclass
class Notice:
    guild_id: int
    channel_id: int
    message_id: int
    created_ts: float

def _write_notice(n: Notice) -> None:
    try:
        NOTICE_PATH.parent.mkdir(parents=True, exist_ok=True)
        NOTICE_PATH.write_text(json.dumps(asdict(n)), encoding="utf-8")
    except Exception:
        pass

def _read_notice() -> Optional[Notice]:
    try:
        obj = json.loads(NOTICE_PATH.read_text(encoding="utf-8"))
        return Notice(**obj)
    except Exception:
        return None

def _clear_notice() -> None:
    try:
        if NOTICE_PATH.exists():
            NOTICE_PATH.unlink()
    except Exception:
        pass

async def mark_before_restart_via_interaction(interaction: discord.Interaction, reason: str = "repo pull_and_restart") -> None:
    """
    Send a non-ephemeral 'Restarting...' message to the current channel and persist its ids.
    Call this BEFORE you actually trigger the restart.
    """
    try:
        ch = interaction.channel
        if not isinstance(ch, (discord.TextChannel, discord.Thread)):
            return
        msg = await ch.send(f"🔁 **Restarting**… ({reason}). Aku akan update pesan ini ketika sudah **Online** ✅")
        n = Notice(
            guild_id=interaction.guild_id or 0,
            channel_id=ch.id,
            message_id=msg.id,
            created_ts=time.time(),
        )
        _write_notice(n)
    except Exception:
        pass

async def finalize_after_ready(bot: discord.Client) -> None:
    """
    On startup, edit the stored message (if any) to show Online + commit,
    otherwise send a compact Online message to LOG channel (if configured).
    """
    n = _read_notice()
    commit = _short_commit()
    text = f"✅ **Online** | commit `{commit}`"
    if n:
        try:
            ch = bot.get_channel(n.channel_id) or await bot.fetch_channel(n.channel_id)  # type: ignore
            if isinstance(ch, (discord.TextChannel, discord.Thread)):
                try:
                    msg = await ch.fetch_message(n.message_id)
                    await msg.edit(content=text)
                    _clear_notice()
                    return
                except Exception:
                    # can't fetch original message; just send a new one
                    await ch.send(text)
                    _clear_notice()
                    return
        except Exception:
            pass
    # Fallback: just post to log channel if set
    if LOG_CH_ID:
        try:
            ch = bot.get_channel(LOG_CH_ID) or await bot.fetch_channel(LOG_CH_ID)  # type: ignore
            if isinstance(ch, (discord.TextChannel, discord.Thread)):
                await ch.send(text)
        except Exception:
            pass
