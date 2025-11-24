from __future__ import annotations

from discord.ext import commands

import os
import asyncio
from typing import Set

DEFAULT_BLOCKLIST = {"⚠️", "⚠"}  # emoji variants

def parse_blocklist(envval: str | None) -> Set[str]:
    if not envval:
        return set(DEFAULT_BLOCKLIST)
    parts = [p.strip() for p in envval.split(",")]
    return {p for p in parts if p}

class WarnReactionBlocker(commands.Cog):
    """Remove/deny warning-style reactions in any channel."""
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.blocklist = parse_blocklist(os.getenv("WARN_REACTION_BLOCKLIST"))
        try:
            delay = float(os.getenv("WARN_REACTION_REMOVE_DELAY_S", "0"))
        except ValueError:
            delay = 0.0
        # Clamp to 0..3s (user requirement)
        self.delay = max(0.0, min(delay, 3.0))

    async def _remove_if_blocked(self, payload):
        emoji_str = payload.emoji.name if hasattr(payload.emoji, "name") and payload.emoji.name else str(payload.emoji)
        if emoji_str not in self.blocklist:
            return
        try:
            channel = self.bot.get_channel(payload.channel_id) or await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            user = self.bot.get_user(payload.user_id) or await self.bot.fetch_user(payload.user_id)
            # remove just the user's reaction if possible
            if self.delay:
                await asyncio.sleep(self.delay)
            await message.remove_reaction(payload.emoji, user)
        except Exception:
            # Ignore all errors (missing perms, message gone, etc.)
            return

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await self._remove_if_blocked(payload)
async def setup(bot: commands.Bot):
    await bot.add_cog(WarnReactionBlocker(bot))