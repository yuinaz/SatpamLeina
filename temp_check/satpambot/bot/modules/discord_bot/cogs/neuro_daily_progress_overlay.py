
from __future__ import annotations
import os, json, urllib.request
from discord.ext import commands

class NeuroDailyProgress(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    async def get_senior_total_raw(self):
        # unified to xp:bot:senior_total
        base = os.getenv("UPSTASH_REDIS_REST_URL","").rstrip("/")
        tok  = os.getenv("UPSTASH_REDIS_REST_TOKEN","")
        if not base or not tok: return None
        req = urllib.request.Request(base + "/get/xp:bot:senior_total", headers={"Authorization": f"Bearer {tok}"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode()).get("result")
