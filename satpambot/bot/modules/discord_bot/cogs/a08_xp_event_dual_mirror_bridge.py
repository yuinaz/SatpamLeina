from __future__ import annotations
import asyncio, json, logging, os, re, time, urllib.parse
from typing import Any, Dict, Optional, Tuple
import discord
from discord.ext import commands

log = logging.getLogger(__name__)
ENABLE = os.getenv("XP_MIRROR_ENABLE", "1") == "1"
INTERVAL_SEC = int(os.getenv("XP_MIRROR_INTERVAL_SEC", "1200"))
SMOKE_MODE = os.getenv("SMOKE_TEST", "0") == "1" or os.getenv("UNIT_TEST", "0") == "1"
UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL", "").strip()
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()
PIN_CH_ID = int(os.getenv("XP_PIN_CHANNEL_ID", "0") or 0)
PIN_MSG_ID = int(os.getenv("XP_PIN_MESSAGE_ID", "0") or 0)
STRICT_EDIT_ONLY = os.getenv("XP_MIRROR_STRICT_EDIT", "1") == "1"
KEYS = ["xp:stage:label","xp:stage:current","xp:stage:required","xp:stage:percent","xp:bot:senior_total","learning:status","learning:status_json"]
JSON_BLOCK_RE = re.compile(r"```json\s*(?P<body>\{.*?\})\s*```", re.S)
def _same(a,b): return (a or "").strip()==(b or "").strip()
class XPEventDualMirrorBridge(commands.Cog):
    def __init__(self, bot): self.bot=bot; self._loop=None; self._ok=False; self._src="none"; self._err=None; self._lock=asyncio.Lock()
    async def cog_load(self): 
        if not ENABLE or SMOKE_MODE: log.info("[xp-mirror] disabled"); return
        log.info("[xp-mirror] loaded; waiting ready")
    @commands.Cog.listener()
    async def on_ready(self):
        if not ENABLE or SMOKE_MODE: return
        if not (UPSTASH_URL and UPSTASH_TOKEN) and not (PIN_CH_ID and PIN_MSG_ID): 
            log.warning("[xp-mirror] no sources configured"); return
        if not self._loop or self._loop.done():
            self._loop=self.bot.loop.create_task(self._run(), name="xp_mirror_loop"); log.info("[xp-mirror] loop started (%ss)", INTERVAL_SEC)
    async def cog_unload(self):
        if self._loop and not self._loop.done(): self._loop.cancel(); 
    @commands.group(name="xp_mirror", invoke_without_command=True)
    @commands.is_owner()
    async def root(self, ctx): await ctx.send(f"[xp-mirror] ok={self._ok} src={self._src} err={self._err}")
    @root.command(name="sync")
    @commands.is_owner()
    async def sync(self, ctx):
        async with self._lock: ok=await self._tick()
        await ctx.send(f"[xp-mirror] sync -> {'OK' if ok else 'FAIL'} src={self._src} err={self._err}")
    async def _run(self):
        await asyncio.sleep(5)
        while True:
            st=time.time()
            try:
                async with self._lock: await self._tick()
            except Exception as e: self._ok=False; self._err=repr(e); log.exception("[xp-mirror] tick err")
            await asyncio.sleep(max(5, INTERVAL_SEC-(time.time()-st)))
    async def _tick(self)->bool:
        ok, up = await self._get_upstash()
        if ok and self._valid(up):
            self._src="upstash"
            pok, pin = await self._get_pin()
            if not pok or not self._same(up,pin): await self._set_pin(up)
            self._ok=True; self._err=None; return True
        pok, pin = await self._get_pin()
        if pok and self._valid(pin):
            self._src="pinned"
            if UPSTASH_URL and UPSTASH_TOKEN: await self._set_upstash(pin)
            self._ok=True; self._err=None; return True
        self._ok=False; self._src="none"; self._err="no valid source"; return False
    def _valid(self,s): 
        if not s: return False
        js=s.get("learning:status_json"); 
        if not js: return False
        try: json.loads(js); return True
        except Exception: return False
    def _same(self,a,b):
        if not a or not b: return False
        for k in KEYS:
            if not _same(a.get(k), b.get(k)): return False
        return True
    async def _get_upstash(self):
        if not (UPSTASH_URL and UPSTASH_TOKEN): return (False,None)
        try: import aiohttp
        except Exception as e: log.warning("[xp-mirror] aiohttp missing: %r", e); return (False,None)
        out={}
        try:
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}
            async with aiohttp.ClientSession(headers=headers) as s:
                for k in KEYS:
                    from urllib.parse import quote
                    url=f"{UPSTASH_URL.rstrip('/')}/get/{quote(k,safe='')}"
                    async with s.get(url, timeout=8) as r:
                        if r.status!=200: log.warning("[xp-mirror] upstash get %s -> %s", k, r.status); return (False,None)
                        data=await r.json(content_type=None); out[k]=("" if data.get("result") is None else str(data.get("result")))
            return (True,out)
        except Exception as e: log.warning("[xp-mirror] fetch upstash failed: %r", e); return (False,None)
    async def _set_upstash(self,snap):
        if not (UPSTASH_URL and UPSTASH_TOKEN): return False
        try: import aiohttp
        except Exception as e: log.warning("[xp-mirror] aiohttp missing: %r", e); return False
        try:
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}
            async with aiohttp.ClientSession(headers=headers) as sess:
                for k in KEYS:
                    from urllib.parse import quote
                    v=snap.get(k,"")
                    url=f"{UPSTASH_URL.rstrip('/')}/set/{quote(k,safe='')}/{quote(v,safe='')}"
                    async with sess.get(url, timeout=8) as r:
                        if r.status!=200: log.warning("[xp-mirror] upstash set %s -> %s", k, r.status); return False
            return True
        except Exception as e: log.warning("[xp-mirror] write upstash failed: %r", e); return False
    async def _get_pin(self):
        if not (PIN_CH_ID and PIN_MSG_ID): return (False,None)
        try:
            ch=await self._resolve(PIN_CH_ID)
            if not ch: log.warning("[xp-mirror] pin channel not found: %s", PIN_CH_ID); return (False,None)
            msg=await ch.fetch_message(PIN_MSG_ID)
        except discord.NotFound: log.warning("[xp-mirror] pin message not found: %s", PIN_MSG_ID); return (False,None)
        except Exception as e: log.warning("[xp-mirror] fetch pinned failed: %r", e); return (False,None)
        m=JSON_BLOCK_RE.search(msg.content or "")
        if not m: return (False,None)
        try:
            parsed=json.loads(m.group("body"))
        except Exception as e: log.warning("[xp-mirror] pinned JSON parse failed: %r", e); return (False,None)
        snap={k:"" for k in KEYS}
        snap["learning:status_json"]=json.dumps(parsed, ensure_ascii=False)
        lab=parsed.get("label"); pct=parsed.get("percent")
        if lab is not None and pct is not None:
            snap["learning:status"]=f"{lab} ({pct:.1f}%)" if isinstance(pct,(int,float)) else str(pct)
        for line in (msg.content or "").splitlines():
            if ":" in line:
                k,v=line.split(":",1); k=k.strip(); v=v.strip()
                if k in KEYS and k not in ("learning:status_json","learning:status") and v: 
                    snap[k]=v
        return (True,snap)
    async def _set_pin(self,snap):
        if not (PIN_CH_ID and PIN_MSG_ID): return False
        try:
            ch=await self._resolve(PIN_CH_ID)
            if not ch: return False
            msg=await ch.fetch_message(PIN_MSG_ID)
        except discord.NotFound:
            if STRICT_EDIT_ONLY: log.warning("[xp-mirror] pin missing & STRICT_EDIT_ONLY=1"); return False
            try:
                ch=await self._resolve(PIN_CH_ID)
                if not ch: return False
                msg=await ch.send(self._compose(snap)); await msg.pin(reason="XP mirror bootstrap"); return True
            except Exception as e: log.warning("[xp-mirror] create pinned failed: %r", e); return False
        except Exception as e: log.warning("[xp-mirror] fetch pinned failed: %r", e); return False
        new=self._compose(snap)
        if (msg.content or "")==new: return True
        try: await msg.edit(content=new); return True
        except Exception as e: log.warning("[xp-mirror] edit pinned failed: %r", e); return False
    async def _resolve(self,ch_id):
        ch=self.bot.get_channel(ch_id)
        if isinstance(ch, discord.TextChannel): return ch
        try:
            ch=await self.bot.fetch_channel(ch_id)
            if isinstance(ch, discord.TextChannel): return ch
        except Exception: return None
        return None
    def _compose(self,snap):
        try: js=json.dumps(json.loads(snap.get("learning:status_json") or "{}"), ensure_ascii=False, separators=(",",":"))
        except Exception: js="{}"
        header=f"**{(snap.get('learning:status') or 'XP Snapshot')}**"
        lines=[header,"","```json",js,"```",""]
        for k in KEYS:
            if k in ("learning:status_json","learning:status"): continue
            v=(snap.get(k) or "").strip()
            if v: lines.append(f"{k}: {v}")
        return "\n".join(lines)

async def setup(bot: commands.Bot):
    if not ENABLE or SMOKE_MODE: log.info("[xp-mirror] loaded but disabled")
    await bot.add_cog(XPEventDualMirrorBridge(bot))


async def _leina_safe_pins(ch, log=None):
    try:
        return await _leina_safe_pins(ch, log)
    except Exception as e:
        status = getattr(e, 'status', None)
        name = getattr(getattr(e, '__class__', None), '__name__', 'Exception')
        if status == 403 or name in ('Forbidden',):
            if log:
                cid = getattr(ch, 'id', '?')
                log.warning('[xp-mirror] pin fetch forbidden ch=%s (50001) → skip', cid)
            return []
        if log: log.warning('[xp-mirror] pin fetch failed: %r', e)
        return []
