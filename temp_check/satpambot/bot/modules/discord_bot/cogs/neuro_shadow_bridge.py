from __future__ import annotations

from discord.ext import commands
import time, json, logging
from pathlib import Path
from typing import Any, Dict
import discord

log = logging.getLogger(__name__)
LOG_PATH = Path("data/shadow_observer.log")

def _append(line: str):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

class NeuroShadowBridge(commands.Cog):
    """Silent file logger for neuro_* events. No messages, no reactions."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        _append(f"[{int(time.time())}] shadow start")

    async def on_neuro_memories_added(self, payload: Dict[str, Any]):
        _append(f"[{int(time.time())}] mems {len(payload.get('items', []))} ch={payload.get('channel_id')}")

    async def on_neuro_xp(self, payload: Dict[str, Any]):
        _append(f"[{int(time.time())}] xp +{payload.get('points')} src={payload.get('source')} ch={payload.get('channel_id')}")

    async def on_neuro_autolearn_summary(self, payload: Dict[str, Any]):
        _append(f"[{int(time.time())}] sum ch={payload.get('channel_id')} len={len(payload.get('summary',''))}")
async def setup(bot: commands.Bot):
    await bot.add_cog(NeuroShadowBridge(bot))