from __future__ import annotations

from discord.ext import commands

import json, itertools, datetime
from pathlib import Path
import discord

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
BANLOG = DATA_DIR / "ban_events.jsonl"

def _read_last(n: int):
    if not BANLOG.exists():
        return []
    # tail last n lines
    lines = BANLOG.read_text(encoding="utf-8").splitlines()
    items = []
    for ln in lines[-n:]:
        try:
            items.append(json.loads(ln))
        except Exception:
            continue
    return items

class BanLogViewer(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="banlog")
    @commands.has_permissions(view_audit_log=True)
    async def banlog(self, ctx: commands.Context, mode: str = "last", count: int = 5):
        """
        !banlog last 5          -> tampilkan 5 ban event terakhir
        !banlog thread 10       -> buat thread dan kirim 10 event terakhir
        """
        last = max(1, min(int(count), 50))
        items = _read_last(last)
        if not items:
            await ctx.reply("(tidak ada data)")
            return

        def make_embed(ev):
            ts = ev.get("ts", "")
            user_id = ev.get("user_id")
            action = ev.get("action", "?")
            reasons = "; ".join(ev.get("reasons", [])) or "-"
            urls = "\\n".join(ev.get("urls", []))[:1000]
            qr = "\\n".join(ev.get("qr", []))[:1000]
            e = discord.Embed(title=f"Ban Log · {action}", color=discord.Color.red(), timestamp=datetime.datetime.fromisoformat(ts.replace('Z','+00:00')) if ts else discord.utils.utcnow())
            e.add_field(name="User ID", value=str(user_id), inline=True)
            e.add_field(name="Reasons", value=reasons, inline=False)
            if urls: e.add_field(name="Text URLs", value=urls, inline=False)
            if qr: e.add_field(name="QR decode", value=qr, inline=False)
            return e

        embeds = [make_embed(ev) for ev in items]
        if mode.lower() == "thread":
            th = await ctx.channel.create_thread(name=f"Ban Log (last {len(embeds)}) {datetime.date.today()}", type=discord.ChannelType.public_thread)
            for e in embeds:
                await th.send(embed=e)
        else:
            for e in embeds:
                await ctx.send(embed=e)
async def setup(bot):
    await bot.add_cog(BanLogViewer(bot))