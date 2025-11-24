
from __future__ import annotations
import os
from discord.ext import commands

def getenv(k, d=None): 
    v = os.getenv(k)
    return v if v not in (None, "") else d

class CurriculumTKSD(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    def key(self):
        return getenv("XP_SENIOR_KEY", "xp:bot:senior_total")
