
# -*- coding: utf-8 -*-
"""
Sticky status (anti-spam, rate-limit friendly).
- Edits exactly one pinned message.
- Guaranteed to update at least once per minute (so uptime moves).
- Single-run guard so multiple loops tidak jalan ganda.
- Internal rate limit backoff jika 429/HTTPException.
Env:
  STATUS_UPDATE_SECONDS=60
  STATUS_RL_MIN_SECONDS=45   # jangan edit lebih rapat dari ini
"""
from __future__ import annotations

import os, math, time, asyncio
from datetime import datetime, timezone
from typing import Optional

import discord
from discord.ext import commands, tasks
from discord.errors import HTTPException

MARKER = "SATPAMBOT_STATUS_V1"
UPDATE_SECONDS = int(os.environ.get("STATUS_UPDATE_SECONDS","60"))
MIN_SPACING = int(os.environ.get("STATUS_RL_MIN_SECONDS","45"))

def _fmt_uptime(sec:int)->str:
    m, s = divmod(max(0,sec), 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m or not parts: parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)

def _lat_ms(bot)->int:
    try:
        v = float(getattr(bot,'latency',0.0) or 0.0)
        if not math.isfinite(v) or v<0: return 0
        return int(v*1000.0)
    except Exception:
        return 0

class StickyStatus(commands.Cog):
    def __init__(self, bot: commands.Bot)->None:
        self.bot = bot
        self._start = time.time()
        self._message_id: Optional[int] = None
        self._last_key: Optional[str] = None
        self._last_edit_ts: float = 0.0
        # single-run guard
        if getattr(bot, "_satpam_status_loop_running", False):
            return
        setattr(bot, "_satpam_status_loop_running", True)
        self._loop.start()

    def _resolve_channel(self)->Optional[discord.TextChannel]:
        raw = os.environ.get("LOG_CHANNEL_ID") or os.environ.get("STATUS_CHANNEL_ID")
        if raw:
            try:
                ch = self.bot.get_channel(int(str(raw).strip()))  # type: ignore
                if ch: return ch  # type: ignore
            except Exception:
                pass
        # fallback by name
        for name in [os.environ.get("LOG_CHANNEL_NAME") or "log-botphising","log-botphishing","bot-log"]:
            for g in list(self.bot.guilds):
                c = discord.utils.get(g.text_channels, name=name)  # type: ignore
                if c: return c  # type: ignore
        return None

    async def _find_or_create(self, ch: discord.TextChannel)->Optional[discord.Message]:
        if self._message_id:
            try:
                return await ch.fetch_message(self._message_id)
            except Exception:
                self._message_id=None
        try:
            async for m in ch.history(limit=50):
                if m.author.id == (self.bot.user.id if self.bot.user else 0):
                    if any((e.footer and e.footer.text and MARKER in e.footer.text) for e in m.embeds) or MARKER in (m.content or ""):
                        self._message_id = m.id
                        return m
        except Exception:
            pass
        msg = await ch.send("Menyiapkan status…")
        self._message_id = msg.id
        try: await msg.pin(reason="SatpamBot • Sticky status")
        except Exception: pass
        return msg

    def _build(self)->tuple[str, discord.Embed]:
        now = datetime.now(timezone.utc)
        me = str(self.bot.user) if self.bot.user else "SatpamBot"
        uptime = _fmt_uptime(int(time.time()-self._start))
        lat = _lat_ms(self.bot)
        e = discord.Embed(title="SatpamBot Status",
                          description="Status ringkas bot.",
                          colour=discord.Colour.green() if self.bot.is_ready() else discord.Colour.orange(),
                          timestamp=now)
        e.add_field(name="Akun", value=me, inline=False)
        e.add_field(name="Presence", value="presence=online" if self.bot.is_ready() else "starting", inline=True)
        e.add_field(name="Uptime", value=uptime, inline=True)
        e.add_field(name="Latency", value=f"{lat} ms", inline=True)
        try: e.add_field(name="Guilds", value=str(len(self.bot.guilds)), inline=True)
        except Exception: pass
        e.set_footer(text=MARKER)
        content=f"✅ Online sebagai {me} | presence=online | uptime={uptime}"
        return content, e

    @tasks.loop(seconds=UPDATE_SECONDS)
    async def _loop(self)->None:
        ch = self._resolve_channel()
        if not ch: return
        msg = await self._find_or_create(ch)
        if not msg: return

        content, embed = self._build()

        # dedup per menit via uptime text + spacing window
        up_field = next((f for f in embed.fields if f.name.lower()=="uptime"), None)
        minute_bucket = "0"
        if up_field and isinstance(up_field.value,str):
            minute_bucket = up_field.value.split(" ")[0]  # "12m"
        key = f"{minute_bucket}|{embed.colour}"

        now = time.time()
        if self._last_key == key and (now - self._last_edit_ts) < max(MIN_SPACING, UPDATE_SECONDS*0.8):
            return

        try:
            await msg.edit(content=content, embed=embed)
            self._last_key = key
            self._last_edit_ts = now
        except HTTPException as e:
            # backoff kalau ke-429
            wait = 5.0
            try:
                if hasattr(e, "status") and e.status == 429:
                    wait = 10.0
            except Exception:
                pass
            await asyncio.sleep(wait)
        except Exception:
            pass

    @_loop.before_loop
    async def _before(self)->None:
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot)->None:
    await bot.add_cog(StickyStatus(bot))
