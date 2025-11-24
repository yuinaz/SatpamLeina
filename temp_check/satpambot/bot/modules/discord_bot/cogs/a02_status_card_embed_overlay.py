# -*- coding: utf-8 -*-
"""
a02_status_card_embed_overlay (enhanced)
- Gabungkan log bot/webhook di STATUS_CHANNEL_ID menjadi 1 embed bertitel "Leina Status"
- Sections: Maintenance, Self-Heal Note, Self-Heal Plan, Errors, Last Action
- Pretty-print JSON otomatis; rate-limit + coalesce edit; persist via Upstash
Commands: !statuscard pin|set|json|clear|rate|show
"""
from discord.ext import commands
import os, re, time, json, logging, asyncio
from typing import Optional, Dict, Tuple

log = logging.getLogger(__name__)

FIELD_LIMIT=1024
SEC_MAP={
 "maintenance":[r"\bmaintenance\b", r"\bmaint(en(ance)?)?\b", r"\bheartbeat\b"],
 "note":[r"\bself[- ]?heal\s+note\b", r"\bnote(s)?\b"],
 "plan":[r"\bself[- ]?heal\s+plan\b", r"\bplan(s)?\b", r"\bappl(ied|y)\b"],
 "errors":[r"\berror(s)?\b", r"\bexception\b", r"\btrace(back)?\b", r"\bfailed\b"],
 "action":[r"\blast\s*action\b", r"\baction(s)?\b", r"\bdispatched\b", r"\blogged\b"],
}
SEC_ORDER=[("maintenance","Maintenance"),("note","Self-Heal Note"),("plan","Self-Heal Plan"),("errors","Errors"),("action","Last Action")]

def _match_section(text):
    s=(text or "").lower()
    for k, pats in SEC_MAP.items():
        for p in pats:
            if re.search(p, s, re.I): return k
    return None

def _strip_fences(s):
    if s is None: return ""
    s=s.strip()
    if s.startswith("```"):
        s=s.strip("`")
        parts=s.split("\n",1)
        if len(parts)==2 and "{" in parts[1]: return parts[1].strip()
        return parts[-1].strip()
    return s

def _pretty_json(s):
    try:
        obj=json.loads(_strip_fences(s))
        return "```json\n"+json.dumps(obj,indent=2,ensure_ascii=False)[:FIELD_LIMIT-10]+"\n```"
    except Exception:
        return None

class _US:
    def __init__(self):
        self.base=(os.getenv("UPSTASH_REDIS_REST_URL","")).rstrip("/")
        self.tok=os.getenv("UPSTASH_REDIS_REST_TOKEN","")
        self.enabled=bool(self.base and self.tok and os.getenv("KV_BACKEND","upstash_rest")=="upstash_rest")
        try: import aiohttp; self.aiohttp=aiohttp
        except Exception as e: self.aiohttp=None; log.warning("[status-card] aiohttp missing: %r", e)
    async def get(self,k):
        if not (self.enabled and self.aiohttp): return None
        url=f"{self.base}/get/{k}"; hdr={"Authorization":f"Bearer {self.tok}"}
        try:
            async with self.aiohttp.ClientSession() as s:
                async with s.get(url,headers=hdr,timeout=8) as r: return (await r.json(content_type=None)).get("result")
        except Exception as e: log.warning("[status-card] GET %s fail: %r", k, e); return None
    async def set(self,k,v):
        if not (self.enabled and self.aiohttp): return False
        url=f"{self.base}/set/{k}/{v}"; hdr={"Authorization":f"Bearer {self.tok}"}
        try:
            async with self.aiohttp.ClientSession() as s:
                async with s.post(url,headers=hdr,timeout=8) as r: return (await r.json(content_type=None)).get("result")=="OK"
        except Exception as e: log.warning("[status-card] SET %s fail: %r", k, e); return False

class StatusCardOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot=bot; self.us=_US()
        self.channel_id=int(os.getenv("STATUS_CHANNEL_ID","1400375184048787566"))
        self.min_sec=int(os.getenv("STATUS_UPDATE_MIN_SEC","10"))
        self._queue=None

    async def _get_msg_id(self):
        v=await self.us.get(f"status_card:{self.channel_id}:message_id")
        try: return int(v) if v else None
        except Exception: return None
    async def _set_msg_id(self,mid): await self.us.set(f"status_card:{self.channel_id}:message_id", str(mid or ""))
    async def _get_ts(self):
        v=await self.us.get(f"status_card:{self.channel_id}:ts") or "0"
        try: return float(v)
        except Exception: return 0.0
    async def _set_ts(self,ts): await self.us.set(f"status_card:{self.channel_id}:ts", str(ts))
    async def _get_data(self):
        raw=await self.us.get(f"status_card:{self.channel_id}:data_json") or "{}"
        try: return json.loads(raw)
        except Exception: return {}
    async def _set_data(self,d): await self.us.set(f"status_card:{self.channel_id}:data_json", json.dumps(d))

    async def _ensure_card(self, text=None):
        ch=self.bot.get_channel(self.channel_id) or await self.bot.fetch_channel(self.channel_id)
        if ch is None: return None
        mid=await self._get_msg_id(); msg=None
        if mid:
            try: msg=await ch.fetch_message(mid)
            except Exception: msg=None
        if msg is None:
            try:
                import discord
                emb=discord.Embed(title="Leina Status", description=text or "Status aktif.")
                data=await self._get_data()
                for key,title in SEC_ORDER:
                    val=(data.get(key) or "").strip()
                    if val: emb.add_field(name=title, value=val[:FIELD_LIMIT], inline=False)
                m=await ch.send(embed=emb)
                try: await m.pin()
                except Exception: pass
                await self._set_msg_id(m.id); return m
            except Exception as e: log.warning("[status-card] create fail: %r", e); return None
        return msg

    async def _render(self, force=False):
        last=await self._get_ts(); now=time.time()
        if not force and now-last<self.min_sec:
            if not self._queue or self._queue.done():
                async def later():
                    await asyncio.sleep(max(0.5, self.min_sec-(now-last)))
                    await self._render(force=True)
                self._queue=asyncio.create_task(later())
            return True
        msg=await self._ensure_card()
        if msg is None: return False
        try:
            import discord
            data=await self._get_data()
            emb= msg.embeds[0] if msg.embeds else discord.Embed(title="Leina Status")
            emb.clear_fields()
            emb.description=f"Status diperbarui • <t:{int(time.time())}:R>"
            for key,title in SEC_ORDER:
                val=(data.get(key) or "").strip()
                if val:
                    if len(val)>FIELD_LIMIT: val=val[:FIELD_LIMIT-2]+" …"
                    emb.add_field(name=title, value=val, inline=False)
            await msg.edit(embed=emb); await self._set_ts(time.time()); return True
        except Exception as e: log.warning("[status-card] render fail: %r", e); return False

    async def _update(self, section, text, render=True):
        d=await self._get_data(); d[section]=text.strip(); await self._set_data(d)
        if render: await self._render()

    def _compose(self, message):
        title=""; body=(getattr(message,"content","") or "").strip()
        if getattr(message,"embeds",None):
            try:
                emb=message.embeds[0]
                if getattr(emb,"title",None): title=emb.title or ""
                if getattr(emb,"description",None):
                    if body: body+="\n"
                    body+=emb.description or ""
                if getattr(emb,"fields",None):
                    f0=emb.fields[0] if emb.fields else None
                    if f0 and getattr(f0,"name",None) and getattr(f0,"value",None):
                        if not title: title=f0.name
                        if body: body+="\n"
                        body += f0.value
            except Exception: pass
        return (title or "").strip(), (body or "").strip()

    @commands.Cog.listener()
    async def on_ready(self):
        await self._ensure_card("Inisialisasi status…")

    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            ch_id=getattr(getattr(message,"channel",None),"id",None)
            if str(ch_id)!=str(self.channel_id): return
            is_webhook=getattr(message,"webhook_id",None) is not None
            if not (getattr(message.author,"bot",False) or is_webhook): return
            title, body = self._compose(message)
            raw=f"{title}\n{body}".strip()
            sec=_match_section(raw) or "note"
            pretty=_pretty_json(body)
            text= pretty if pretty else ("\n".join(ln for ln in body.splitlines() if ln.strip()) or "[update]")
            await self._update(sec, text, render=True)
            try: await message.delete()
            except Exception: pass
        except Exception as e: log.warning("[status-card] on_message err: %r", e)

    @commands.group(name="statuscard", invoke_without_command=True)
    async def g_root(self, ctx):
        data=await self._get_data()
        await ctx.reply(f"📌 status-card channel={self.channel_id} sections={list(data.keys())}", mention_author=False)

    @g_root.command(name="pin")
    async def g_pin(self, ctx):
        m=await self._ensure_card("Status aktif.")
        await ctx.reply("📌 pinned" if m else "❌ gagal pin", mention_author=False)

    @g_root.command(name="set")
    async def g_set(self, ctx, section: str, *, text: str):
        section=section.lower().strip()
        if section not in ("maintenance","note","plan","errors","action"):
            return await ctx.reply("❌ section tidak dikenal. Gunakan: maintenance|note|plan|errors|action", mention_author=False)
        await self._update(section, text, render=True); await ctx.reply("✅ updated", mention_author=False)

    @g_root.command(name="json")
    async def g_json(self, ctx, section: str, *, payload: str):
        section=section.lower().strip()
        if section not in ("maintenance","note","plan","errors","action"):
            return await ctx.reply("❌ section tidak dikenal. Gunakan: maintenance|note|plan|errors|action", mention_author=False)
        pp=_pretty_json(payload)
        if not pp: return await ctx.reply("❌ payload bukan JSON yang valid.", mention_author=False)
        await self._update(section, pp, render=True); await ctx.reply("✅ updated (json)", mention_author=False)

    @g_root.command(name="clear")
    async def g_clear(self, ctx, section: str):
        section=section.lower().strip()
        d=await self._get_data()
        if section in d:
            d[section]=""; await self._set_data(d); await self._render(force=True)
            await ctx.reply("🧹 cleared", mention_author=False)
        else:
            await ctx.reply("ℹ️ section kosong/tdk ada", mention_author=False)

    @g_root.command(name="rate")
    async def g_rate(self, ctx, sec: int):
        self.min_sec=max(1,int(sec)); await ctx.reply(f"⏱️ rate limit di-set {self.min_sec}s", mention_author=False)

    @g_root.command(name="show")
    async def g_show(self, ctx):
        ok=await self._render(force=True); await ctx.reply("🔄 refreshed" if ok else "❌ gagal render", mention_author=False)
async def setup(bot):
    await bot.add_cog(StatusCardOverlay(bot))
def setup(bot):
    try:
        import asyncio; loop=None
        try: loop=asyncio.get_event_loop()
        except RuntimeError: pass
        return loop.create_task(setup(bot)) if (loop and loop.is_running()) else asyncio.run(setup(bot))
    except Exception: return None