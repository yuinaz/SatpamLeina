
"""
neuro_memory_pinner_fix.py
Idempotent memory pinner for neuro-lite progress. Ensures single embed updated, never repinned/recreated.
"""
import logging
from typing import Optional
import discord
from satpambot.bot.modules.discord_bot.helpers import memory_upsert_fix as memfix  # type: ignore

LOG = logging.getLogger(__name__)

TITLE = "[[neuro-lite:gate]] NEURO-LITE GATE STATUS"
THREAD = "neuro-lite progress"

class NeuroLiteMemoryPinnerFix:
    def __init__(self, bot: discord.Client):
        self.bot = bot

    async def upsert_gate(self, description: str):
        payload = {"text": description}
        await memfix.upsert_json(self.bot, TITLE, payload, THREAD)

def setup(bot):
    bot.neuro_pinner_fix = NeuroLiteMemoryPinnerFix(bot)
    LOG.info("[neuro_pinner_fix] ready (idempotent)")
