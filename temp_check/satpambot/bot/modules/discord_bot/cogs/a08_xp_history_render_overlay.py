
from __future__ import annotations
import os, json, urllib.request
from discord.ext import commands

def _cfg(k, d):
    return os.getenv(k, d)

SENIOR_KEY = _cfg("XP_SENIOR_KEY", "xp:bot:senior_total")

class XPHistoryRender(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
