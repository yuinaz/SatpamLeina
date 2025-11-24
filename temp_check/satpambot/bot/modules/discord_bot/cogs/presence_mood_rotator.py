# -*- coding: utf-8 -*-
from __future__ import annotations

from discord.ext import commands

import os, json, random, asyncio, datetime, contextlib, logging
from typing import Optional
import discord

log = logging.getLogger(__name__)

CFG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..", "..", "config", "presence_mood_rotator.json")
FTAB_LEARN_JSON = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..", "..", "config", "first_touch_learning.json")

def _load_json(path, fallback):
    try:
        import json
        with open(path, "r", encoding="utf-8") as f: d = json.load(f); return d if isinstance(d, (dict, list)) else fallback
    except Exception: return fallback

def _status_from_str(s: str) -> discord.Status:
    return {"online": discord.Status.online, "idle": discord.Status.idle, "dnd": discord.Status.dnd, "invisible": discord.Status.invisible}.get((s or "").lower(), discord.Status.online)

def _activity(tp: str, name: str) -> discord.Activity:
    t = (tp or "").lower()
    if t == "watching":  return discord.Activity(type=discord.ActivityType.watching, name=name)
    if t == "listening": return discord.Activity(type=discord.ActivityType.listening, name=name)
    if t == "competing": return discord.Activity(type=discord.ActivityType.competing, name=name)
    return discord.Game(name=name)

class PresenceMoodRotator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task: Optional[asyncio.Task] = None
        self._last: Optional[str] = None
        self.cfg = _load_json(CFG_PATH, {})
        self.cfg.setdefault("interval_minutes", 120)
        self.cfg.setdefault("default_status", "online")
        self.cfg.setdefault("weights", {"tod": 0.5, "ftab": 0.5})
        self.cfg.setdefault("moods", {})

    def _compute_mood(self) -> str:
        now = datetime.datetime.now(); h = now.hour
        mood_tod = "sleeping" if h<6 else "calm" if h<12 else "helpful" if h<18 else "alert"
        learn = _load_json(FTAB_LEARN_JSON, {"safe": [], "bad": []})
        safe_n, bad_n = len(learn.get("safe") or []), len(learn.get("bad") or [])
        if bad_n > safe_n * 1.2 and bad_n >= 5: mood_ftab = "alert"
        elif safe_n > bad_n * 1.5 and safe_n >= 5: mood_ftab = "helpful"
        elif safe_n + bad_n <= 2: mood_ftab = "calm"
        else: mood_ftab = "calm"
        w = self.cfg.get("weights", {"tod": 0.5, "ftab": 0.5})
        def S(m): return {"sleeping":0.0,"calm":0.4,"helpful":0.7,"alert":1.0}[m]
        sc = w.get("tod",0.5)*S(mood_tod) + w.get("ftab",0.5)*S(mood_ftab)
        return "alert" if sc>=0.85 else "helpful" if sc>=0.6 else "calm" if sc>=0.3 else "sleeping"

    def _pick(self, mood: str):
        moods = self.cfg.get("moods") or {}
        lst = moods.get(mood) or moods.get("helpful") or []
        if not lst: return None
        random.shuffle(lst)
        for a in lst:
            k = f"{a.get('type')}::{a.get('name')}"
            if k != self._last:
                self._last = k
                return a
        return lst[0]

    async def _apply(self):
        mood = self._compute_mood()
        a = self._pick(mood) or {"type":"playing", "name":"🛡️ standby"}
        with contextlib.suppress(Exception):
            await self.bot.change_presence(status=_status_from_str(self.cfg.get("default_status","online")), activity=_activity(a.get("type"), a.get("name")))

    async def _runner(self):
        await self.bot.wait_until_ready()
        await self._apply()
        interval = max(10, int(self.cfg.get("interval_minutes", 120)))
        while not self.bot.is_closed():
            await asyncio.sleep(interval*60)
            await self._apply()

    @commands.Cog.listener()
    async def on_ready(self):
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._runner())
async def setup(bot: commands.Bot):
    if bot.get_cog("PresenceMoodRotator") is None:
        await bot.add_cog(PresenceMoodRotator(bot))