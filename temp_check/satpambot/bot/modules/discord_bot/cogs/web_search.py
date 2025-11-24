from __future__ import annotations

from discord.ext import commands
import logging, json
from typing import List, Dict, Any, Optional
import discord

from satpambot.config.local_cfg import cfg

log = logging.getLogger(__name__)

def _owner_only_enabled() -> bool:
    return bool(cfg("SEARCH_OWNER_ONLY", True))

def _max_results() -> int:
    try: return int(cfg("SEARCH_MAX_RESULTS", 5))
    except Exception: return 5

def _provider() -> str:
    return str(cfg("SEARCH_PROVIDER", "auto")).lower()

def _owner_id() -> Optional[int]:
    try:
        v = cfg("OWNER_USER_ID", None)
        return int(v) if v is not None else None
    except Exception:
        return None

async def _search(query: str, n: int = 5) -> List[Dict[str, Any]]:
    prov = _provider()
    serpapi_key = cfg("SERPAPI_KEY", None) or (cfg("secrets", {}) or {}).get("serpapi_key")
    serper_key  = cfg("SERPER_API_KEY", None) or (cfg("secrets", {}) or {}).get("serper_api_key")
    # SerpAPI
    if prov in ("auto","serpapi") and serpapi_key:
        try:
            import aiohttp
            params = {"engine":"google","q":query,"api_key":serpapi_key,"num":n}
            async with aiohttp.ClientSession() as sess:
                async with sess.get("https://serpapi.com/search.json", params=params, timeout=20) as r:
                    data = await r.json()
            out = []
            for item in (data.get("organic_results") or [])[:n]:
                out.append({"title": item.get("title",""), "url": item.get("link",""), "snippet": item.get("snippet","")})
            if out: return out
        except Exception as e:
            log.warning("SerpAPI failed: %s", e)
    # Serper
    if prov in ("auto","serper") and serper_key:
        try:
            import aiohttp
            payload = {"q": query, "num": n}
            headers = {"X-API-KEY": serper_key, "Content-Type": "application/json"}
            async with aiohttp.ClientSession() as sess:
                async with sess.post("https://google.serper.dev/search", data=json.dumps(payload), headers=headers, timeout=20) as r:
                    data = await r.json()
            out = []
            for item in (data.get("organic") or [])[:n]:
                out.append({"title": item.get("title",""), "url": item.get("link",""), "snippet": item.get("snippet","")})
            if out: return out
        except Exception as e:
            log.warning("Serper failed: %s", e)
    # DuckDuckGo fallback (no API key)
    try:
        from duckduckgo_search import DDGS
        out = []
        with DDGS() as ddgs:
            for i, res in enumerate(ddgs.text(query, max_results=max(3, n))):
                if i >= n: break
                out.append({"title": res.get("title",""), "url": res.get("href",""), "snippet": res.get("body","")})
        if out: return out
    except Exception as e:
        log.warning("duckduckgo_search missing or failed: %s", e)
    return []

def _is_owner(user: discord.abc.User) -> bool:
    oid = _owner_id()
    return (oid is not None) and (int(user.id) == int(oid))

class WebSearch(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="search", description="Cari info di web (SerpAPI/Serper/DDG).")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def search(self, ctx: commands.Context, *, query: str):
        if _owner_only_enabled() and not await self._owner_or_dm(ctx):
            return await self._deny(ctx, "Perintah ini sementara hanya untuk **Owner**.")
        await ctx.defer(ephemeral=False)
        results = await _search(query, _max_results())
        if not results:
            hint = "Pasang `duckduckgo-search` atau isi key SerpAPI/Serper di `local.json`."
            return await ctx.reply(f"❌ Tidak bisa mencari saat ini. {hint}")
        embed = discord.Embed(title=f"Web Search: {query}", colour=discord.Colour.blurple())
        for i, r in enumerate(results, 1):
            title = r.get("title") or "(tanpa judul)"
            url = r.get("url") or ""
            snippet = (r.get("snippet") or "").strip()
            snippet = (snippet[:300] + "…") if len(snippet) > 300 else snippet
            value = url if not snippet else f"{url}\n{snippet}"
            embed.add_field(name=f"{i}. {title}", value=value, inline=False)
        await ctx.reply(embed=embed)

    async def _owner_or_dm(self, ctx: commands.Context) -> bool:
        try:
            if ctx.guild is None:
                return True
            return _is_owner(ctx.author) or (await self.bot.is_owner(ctx.author))
        except Exception:
            return False

    async def _deny(self, ctx: commands.Context, msg: str):
        try:
            await ctx.reply(msg, delete_after=15)
        except Exception:
            pass
async def setup(bot: commands.Bot):
    await bot.add_cog(WebSearch(bot))