from __future__ import annotations

from discord.ext import commands

import os
from datetime import datetime
from zoneinfo import ZoneInfo
import discord
from discord.ext import tasks

from ..helpers import progress_gate as gate

def _tz():
    try:
        return ZoneInfo(os.getenv("BOT_TZ", "Asia/Jakarta"))
    except Exception:
        return None

def _owners():
    raw = os.getenv("DISCORD_OWNER_IDS") or os.getenv("OWNER_IDS") or ""
    res = []
    for p in raw.replace(";", ",").split(","):
        p = p.strip()
        if not p:
            continue
        try:
            res.append(int(p))
        except Exception:
            pass
    return res

class LearningProgressReporter(commands.Cog):
    """Kirim ringkasan progress ke owner: harian, mingguan, bulanan (DM)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.daily.start()
        self.weekly.start()
        self.monthly.start()

    def cog_unload(self):
        self.daily.cancel()
        self.weekly.cancel()
        self.monthly.cancel()

    @tasks.loop(hours=24.0)
    async def daily(self):
        await self._send_report("daily")

    @tasks.loop(hours=24.0*7)
    async def weekly(self):
        await self._send_report("weekly")

    @tasks.loop(hours=24.0*30)
    async def monthly(self):
        await self._send_report("monthly")

    async def _send_report(self, kind: str):
        prog = gate.get_progress()
        tz = _tz()
        now = datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M %Z")
        text = (
            f"📈 **Learning Progress ({kind})** — {now}\n"
            f"- Progress: {prog.ratio*100:.2f}%\n"
            f"- Akurasi (shadow): {prog.accuracy*100:.2f}%\n"
            f"- Sampel: {prog.samples}\n"
            f"- Threshold publik: {gate.required_ratio()*100:.0f}%\n"
            f"- Public mode: {'ON' if gate.is_public_allowed() else 'OFF'}\n"
        )
        for oid in _owners():
            try:
                user = self.bot.get_user(oid) or await self.bot.fetch_user(oid)  # type: ignore
                await user.send(text)
            except Exception:
                pass
async def setup(bot: commands.Bot):
    await bot.add_cog(LearningProgressReporter(bot))