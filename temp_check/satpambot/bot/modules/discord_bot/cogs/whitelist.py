from __future__ import annotations

from discord.ext import commands

import json, os
from pathlib import Path
import discord

DATA_DIR = Path(os.getenv("DATA_DIR") or "data")
WL_FILE = Path(os.getenv("WHITELIST_DOMAINS_FILE") or (DATA_DIR / "whitelist_domains.json"))

def _load():
    try:
        return set(json.loads(WL_FILE.read_text(encoding="utf-8")))
    except Exception:
        return set()

def _save(s: set[str]):
    WL_FILE.parent.mkdir(parents=True, exist_ok=True)
    WL_FILE.write_text(json.dumps(sorted(s), ensure_ascii=False, indent=2), encoding="utf-8")

class WhiteList(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.has_permissions(manage_guild=True)
    @commands.command(name="whitelist")
    async def whitelist(self, ctx: commands.Context, action: str = "", *, domain: str = ""):
        action = (action or "").lower().strip()
        d = (domain or "").lower().strip()
        wl = _load()

        if action == "add" and d:
            wl.add(d); _save(wl)
            return await ctx.reply(f"✅ Ditambahkan ke whitelist: `{d}`", mention_author=False)
        if action in ("del","remove") and d:
            if d in wl:
                wl.remove(d); _save(wl)
            return await ctx.reply(f"✅ Dihapus dari whitelist: `{d}`", mention_author=False)
        if action in ("list","ls"):
            items = "\n".join(f"• {x}" for x in sorted(wl)) or "(kosong)"
            return await ctx.reply(f"**Whitelist domains:**\n{items}", mention_author=False)

        return await ctx.reply("Gunakan: `!whitelist add <domain>` / `!whitelist remove <domain>` / `!whitelist list`", mention_author=False)
async def setup(bot): await bot.add_cog(WhiteList(bot))