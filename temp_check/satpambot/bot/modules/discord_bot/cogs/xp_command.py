from __future__ import annotations
from discord.ext import commands

import json, os
from pathlib import Path
import discord

from satpambot.config.local_cfg import cfg

ROOT = Path(__file__).resolve().parents[5]
DATA_DIR = ROOT / "data/neuro-lite"
PROGRESS = DATA_DIR / "progress.json"
JR = DATA_DIR / "learn_progress_junior.json"
SR = DATA_DIR / "learn_progress_senior.json"

ALLOWED_CHANNELS = {int(x) for x in str(cfg("XP_ALLOWED_CHANNEL_IDS", "1425400701982478408 1426397317598154844 1426571542627614772")).split() if x.isdigit()}
def _load_json(p: Path):
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}

class XPCommand(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.hybrid_command(name="xp", description="Tampilkan XP & level belajar saat ini")
    async def xp(self, ctx: commands.Context):
        # channel guard (prevent spam di umum)
        ch_id = getattr(ctx.channel, "id", 0)
        if ALLOWED_CHANNELS and ch_id not in ALLOWED_CHANNELS:
            try:
                await ctx.reply("Gunakan perintah ini di thread **neuro-lite progress**, **Learning Progress**, atau **QnA belajar** ya.", ephemeral=True)  # slash ephemeral
            except Exception:
                await ctx.reply("Gunakan perintah ini di thread progress/QnA yang disetujui ya.")
            return

        p = _load_json(PROGRESS)
        jr = _load_json(JR)
        sr = _load_json(SR)

        total = int(p.get("xp", p.get("total", 0)) or 0)
        lvl   = str(p.get("level", "N/A"))
        today = int(p.get("today", 0) or 0)

        def _sum_levels(tree) -> str:
            if not isinstance(tree, dict): return "-"
            out = []
            for k,v in tree.items():
                if isinstance(v, dict):
                    s = sum(int(x or 0) for x in v.values() if isinstance(x, (int, float)))
                    out.append(f"{k}: {s}")
            return ", ".join(out) or "-"

        jr_sum = _sum_levels(jr)
        sr_sum = _sum_levels(sr)

        emb = discord.Embed(title="Learning XP", description="Ringkasan progres saat ini")
        emb.add_field(name="Total XP", value=f"**{total}**", inline=True)
        emb.add_field(name="Hari ini", value=f"{today}", inline=True)
        emb.add_field(name="Level", value=str(lvl), inline=True)
        if jr_sum != "-" or sr_sum != "-":
            emb.add_field(name="Junior (ringkas)", value=jr_sum or "-", inline=False)
            emb.add_field(name="Senior (ringkas)", value=sr_sum or "-", inline=False)
        emb.set_footer(text="SatpamLeina • /xp")

        # Prefer reply to keep thread rapi
        try:
            await ctx.reply(embed=emb)
        except Exception:
            await ctx.send(embed=emb)

async def setup(bot): await bot.add_cog(XPCommand(bot))