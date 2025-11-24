from __future__ import annotations

from discord.ext import commands

import os, re, random
import discord

from ..helpers import env_store

def _get_names():
    raw = env_store.get("WAKE_NAMES") or os.getenv("WAKE_NAMES") or "Leina,SatpamLeina"
    names = [x.strip() for x in re.split(r"[;,/| ]+", raw) if x.strip()]
    return names or ["Leina"]
AUTO = (env_store.get("WAKE_NAME_AUTO") or os.getenv("WAKE_NAME_AUTO") or "1") == "1"

class NameWakeAutoReply(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.names = _get_names()
        self.pattern = re.compile(r"\b(" + "|".join(re.escape(n) for n in self.names) + r")\b", re.I)

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.bot: return
        if not AUTO: return
        if self.pattern.search(msg.content or ""):
            # simple expressive reply; real persona handled by ChatNeuroLite
            replies = [
                "Hah? dipanggil aku ya~ www",
                "Iya? ada apa sih… (tsun)",
                "Hehe iya, aku di sini~",
                "Nani? (＞﹏＜)",
            ]
            try:
                await msg.channel.send(random.choice(replies))
            except Exception:
                pass
async def setup(bot):
    await bot.add_cog(NameWakeAutoReply(bot))