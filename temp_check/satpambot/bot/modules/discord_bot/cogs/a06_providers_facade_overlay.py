
from discord.ext import commands
"""
a06_providers_facade_overlay.py
- Expose LLM/STT/TTS providers via Cog so other cogs can access easily.
"""
import logging

from satpambot.bot.providers.llm import LLM
from satpambot.bot.providers.stt import STT
from satpambot.bot.providers.tts import TTS

log = logging.getLogger(__name__)

class ProvidersOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.llm = LLM()
        self.stt = STT()
        self.tts = TTS()
async def setup(bot):
    await bot.add_cog(ProvidersOverlay(bot))

def setup(bot):
    try:
        import asyncio
        if asyncio.get_event_loop().is_running():
            return asyncio.create_task(bot.add_cog(ProvidersOverlay(bot)))
    except Exception: pass
    return bot.add_cog(ProvidersOverlay(bot))