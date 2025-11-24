from discord.ext import commands

"""
a22_force_senior_overlay.py
---------------------------
Gentle nudge to prefer the 'senior' curriculum track.
This uses an env flag many modules check; safe no-op if ignored.
"""
import os, logging
log = logging.getLogger(__name__)
os.environ.setdefault("CURRICULUM_FORCE_SENIOR", "1")
os.environ.setdefault("CURRICULUM_PREF", "senior")
log.info("[senior-overlay] set CURRICULUM_FORCE_SENIOR=1, CURRICULUM_PREF=senior")

class _SeniorOverlay:
    def __init__(self, bot):  # pragma: no cover
        self.bot = bot

async def setup(bot):  # pragma: no cover
    _SeniorOverlay(bot)