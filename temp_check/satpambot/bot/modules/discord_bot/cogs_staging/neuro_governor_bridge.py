from __future__ import annotations

# satpambot/bot/modules/discord_bot/cogs/neuro_governor_bridge.py

import contextlib
import importlib
from typing import Optional

import discord
from discord.ext import commands

try:
    # Optional external governor module; user may ship it in this zip.
    GOV = importlib.import_module("neuro_governor")
except Exception:
    GOV = None


class NeuroGovernorBridge(commands.Cog):
    """Bridge events into external neuro_governor if present; otherwise no-op."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_neuro_signal")
    async def _forward(self, sig):
        if GOV is None:
            return
        with contextlib.suppress(Exception):
            if hasattr(GOV, "ingest_signal"):
                GOV.ingest_signal(sig)


async def setup(bot: commands.Bot):
    await bot.add_cog(NeuroGovernorBridge(bot))
