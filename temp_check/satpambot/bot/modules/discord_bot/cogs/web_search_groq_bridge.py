from __future__ import annotations

from discord.ext import commands
import logging, os, httpx, asyncio, time
from typing import List, Dict, Any
import discord

from discord import app_commands
import os

log = logging.getLogger(__name__)

SERPER_KEY = os.getenv("SERPER_API_KEY") or os.getenv("serper_api_key")
SERPAPI_KEY = os.getenv("SERPAPI_KEY") or os.getenv("serpapi_key")
GROQ_KEY = os.getenv("GROQ_API_KEY") or os.getenv("groq_api_key")

SEARCH_PROVIDER = (os.getenv("SEARCH_PROVIDER") or "auto").lower()

QNA_ONLY = (os.getenv("SEARCH_OWNER_ONLY") or os.getenv("SEARCH_QNA_ONLY") or "true").lower() in ("1","true","yes","on")
QNA_CHANNEL_ID = int(os.getenv("LEARNING_QNA_CHANNEL_ID") or "0")
MAX_RESULTS = int(os.getenv("SEARCH_MAX_RESULTS") or "5")

HEADERS = {"User-Agent": "satpambot/1.0 (+search)"}

def _allow_ctx(ctx: commands.Context) -> bool:
    # Allow in QNA channel or owner DMs
    if ctx.guild is None:
        # DM: allow only owner by permissions on your existing guards
        return True
    if QNA_ONLY and QNA_CHANNEL_ID and int(ctx.channel.id) != QNA_CHANNEL_ID:
        return False
    return True

async def serper_search(q: str) -> List[Dict[str, Any]]:
    if not SERPER_KEY:
        return []
    url = "https://google.serper.dev/search"
    payload = {"q": q, "num": MAX_RESULTS}
    async with httpx.AsyncClient(timeout=15.0, headers={"X-API-KEY": SERPER_KEY, **HEADERS}) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        items = []
        for it in (data.get("organic") or [])[:MAX_RESULTS]:
            items.append({"title": it.get("title"), "url": it.get("link"), "snippet": it.get("snippet")})
        return items

async def serpapi_search(q: str) -> List[Dict[str, Any]]:
    if not SERPAPI_KEY:
        return []
    url = "https://serpapi.com/search.json"
    params = {"engine":"google", "q": q, "num": MAX_RESULTS, "api_key": SERPAPI_KEY}
    async with httpx.AsyncClient(timeout=15.0, headers=HEADERS) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        items = []
        for it in (data.get("organic_results") or [])[:MAX_RESULTS]:
            items.append({"title": it.get("title"), "url": it.get("link"), "snippet": it.get("snippet")})
        return items

async def groq_rewrite(q: str) -> str:
    if not GROQ_KEY:
        return q
    # Minimal prompt to improve query
    payload = {
        "messages":[{"role":"system","content":"Rewrite the user query for a web search engine. Keep concise."},
                    {"role":"user","content":q}],
        "model": os.getenv("GROQ_MODEL","llama-3.1-8b-instant"),
        "temperature": 0.2,
        "max_tokens": 64,
        "stream": False
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post("https://api.groq.com/openai/v1/chat/completions",
                              headers={"Authorization": f"Bearer {GROQ_KEY}"},
                              json=payload)
        r.raise_for_status()
        data = r.json()
        return (data.get("choices",[{}])[0].get("message",{}).get("content") or q).strip()

async def groq_summarize(q: str, items: List[Dict[str,Any]]) -> str:
    if not GROQ_KEY or not items:
        return ""
    content = "Query: {}\nResults:\n".format(q)
    for i, it in enumerate(items, 1):
        content += f"{i}. {it.get('title')} — {it.get('url')}\n{it.get('snippet')}\n"
    payload = {
        "messages":[{"role":"system","content":"Summarize results into 3-5 bullet points with links."},
                    {"role":"user","content":content}],
        "model": os.getenv("GROQ_MODEL","llama-3.1-8b-instant"),
        "temperature": 0.2,
        "max_tokens": 300,
        "stream": False
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post("https://api.groq.com/openai/v1/chat/completions",
                              headers={"Authorization": f"Bearer {GROQ_KEY}"},
                              json=payload)
        r.raise_for_status()
        data = r.json()
        return (data.get("choices",[{}])[0].get("message",{}).get("content") or "").strip()


def _get_gemini_model():
    return os.getenv("LLM_GEMINI_MODEL") or os.getenv("GEMINI_MODEL") or "gemini-2.5-flash-lite"



def _get_groq_model():
    return os.getenv("LLM_GROQ_MODEL") or "llama-3.1-8b-instant"


class WebSearchGroq(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="websearch", with_app_command=True, description="Cari di web (QnA channel).")
    async def websearch(self, ctx: commands.Context, *, query: str):
        if not _allow_ctx(ctx):
            return await ctx.reply("Gunakan perintah ini di channel QnA.", mention_author=False, delete_after=10)
        q2 = await groq_rewrite(query)
        items = []
        if SEARCH_PROVIDER in ("auto","serper"):
            try:
                items = await serper_search(q2)
            except Exception as e:
                log.warning("serper failed: %s", e)
        if not items and SEARCH_PROVIDER in ("auto","serpapi"):
            try:
                items = await serpapi_search(q2)
            except Exception as e:
                log.warning("serpapi failed: %s", e)
        if not items:
            return await ctx.reply("Tidak ada hasil / provider belum diset API key.", mention_author=False)
        summary = await groq_summarize(q2, items) if GROQ_KEY else ""
        view_lines = [f"**{it['title']}**\n<{it['url']}>\n{it['snippet']}" for it in items]
        text = "\n\n".join(view_lines[:MAX_RESULTS])
        if summary:
            text = f"**Ringkasan:**\n{summary}\n\n{text}"
        await ctx.reply(text[:1900], suppress_embeds=False, mention_author=False)
async def setup(bot: commands.Bot):
    await bot.add_cog(WebSearchGroq(bot))