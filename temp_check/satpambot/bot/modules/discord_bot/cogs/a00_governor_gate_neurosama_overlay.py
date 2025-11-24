# -*- coding: utf-8 -*-
"""
Governor Gate (Neurosama-style) — SPEAK policy only (v3)
- QnA/Auto-learn stays running ALWAYS.
- Gate controls WHERE the bot may REPLY (speak), not learning.
- Modes:
   * LOCKED/quarantine: bot may reply ONLY in LEARN_CHANNEL_ID.
   * UNLOCKED: bot may reply ONLY in PUBLIC_CHANNELS (persisted).
- LEARN channel is ALWAYS allowed (both modes). Others: silent (but learns).

Admin commands:
  !gate status | !gate lock | !gate unlock
  !interview start | !interview pass | !interview fail
  !go public [channel_id]      -> add channel to allowlist (persist)
  !go revoke [channel_id]      -> remove channel from allowlist (persist)
  !go list                     -> show current allowlist

Persistence (Upstash JSON):
  governor:public_channels_json = "[886534544688308265, ...]"

ENV:
  LEARN_CHANNEL_ID      default: 1426571542627614772
  PUBLIC_CHANNEL_ID     default bootstrap: 886534544688308265 (seed into list if empty)
  GOVERNOR_SENIOR_THRESHOLD default: 80000
  ADMIN_USER_IDS        comma separated Discord user IDs
  KV_BACKEND=upstash_rest, UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN
"""
from discord.ext import commands
import os, asyncio, logging, re, json
from typing import Optional, List

log = logging.getLogger(__name__)

class _Upstash:
    def __init__(self):
        self.base = os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/")
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
        self.enabled = bool(self.base and self.token and os.getenv("KV_BACKEND", "upstash_rest") == "upstash_rest")
        try:
            import aiohttp
            self._aiohttp = aiohttp
        except Exception as e:
            self._aiohttp = None
            log.warning("[governor] aiohttp not available: %r", e)
    async def get(self, key: str):
        if not self.enabled or not self._aiohttp: return None
        url = f"{self.base}/get/{key}"
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            async with self._aiohttp.ClientSession() as s:
                async with s.get(url, headers=headers, timeout=8) as r:
                    data = await r.json(content_type=None)
                    return data.get("result")
        except Exception as e:
            log.warning("[governor] Upstash GET %s failed: %r", key, e)
            return None
    async def set(self, key: str, value: str) -> bool:
        if not self.enabled or not self._aiohttp: return False
        url = f"{self.base}/set/{key}/{value}"
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            async with self._aiohttp.ClientSession() as s:
                async with s.post(url, headers=headers, timeout=8) as r:
                    data = await r.json(content_type=None)
                    return data.get("result") == "OK"
        except Exception as e:
            log.warning("[governor] Upstash SET %s failed: %r", key, e)
            return False

def _env_int(name: str, d: int) -> int:
    try: return int(os.getenv(name, str(d)).strip())
    except Exception: return d
def _env_ids(name: str):
    raw = os.getenv(name, "").strip()
    out = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit(): out.append(int(part))
    return out

_QNA_HEUR = re.compile(r"^\s*q\s*[:\-]", re.I)
_LEINA_HEUR = re.compile(r"(@?leina|<@!?\d+>)", re.I)

class GovernorGate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.us = _Upstash()
        self.learn_ch = int(os.getenv("LEARN_CHANNEL_ID", "1426571542627614772"))
        self.public_ch_default = int(os.getenv("PUBLIC_CHANNEL_ID", "886534544688308265"))
        self.senior_threshold = _env_int("GOVERNOR_SENIOR_THRESHOLD", 80000)
        self.admin_ids = set(_env_ids("ADMIN_USER_IDS"))
        self._patch_done = False
    async def _kv_bool(self, key: str, default: bool) -> bool:
        v = await self.us.get(key)
        if v is None: return default
        vv = str(v).strip().lower()
        if vv in ("1","true","on","yes"): return True
        if vv in ("0","false","off","no",""): return False
        try: return bool(int(v))
        except Exception: return default
    async def _set_bool(self, key: str, val: bool) -> bool:
        return await self.us.set(key, "1" if val else "0")
    async def _kv_json_list(self, key: str):
        raw = await self.us.get(key)
        if not raw:
            return []
        try:
            arr = json.loads(raw)
            out = []
            for x in arr:
                try: out.append(int(x))
                except Exception: continue
            return out
        except Exception:
            return []
    async def _kv_set_json_list(self, key: str, lst):
        try:
            s = json.dumps(sorted(list(set(int(x) for x in lst))))
        except Exception:
            s = "[]"
        return await self.us.set(key, s)
    async def get_state(self):
        locked   = await self._kv_bool("governor:gate_locked", True)
        req      = await self._kv_bool("governor:interview_required", True)
        ok       = await self._kv_bool("governor:interview_passed", False)
        public   = await self._kv_bool("governor:public_enabled", False)
        pubs     = await self._kv_json_list("governor:public_channels_json")
        if not pubs:
            pubs = [self.public_ch_default]
            await self._kv_set_json_list("governor:public_channels_json", pubs)
        return locked, req, ok, public, pubs
    async def set_public_enabled(self, on: bool): await self._set_bool("governor:public_enabled", on)
    async def set_gate_locked(self, on: bool):    await self._set_bool("governor:gate_locked", on)
    async def set_interview(self, required=None, passed=None):
        if required is not None: await self._set_bool("governor:interview_required", required)
        if passed is not None:   await self._set_bool("governor:interview_passed", passed)
    async def add_public_channel(self, ch_id: int):
        pubs = await self._kv_json_list("governor:public_channels_json")
        if ch_id not in pubs:
            pubs.append(ch_id)
            await self._kv_set_json_list("governor:public_channels_json", pubs)
    async def remove_public_channel(self, ch_id: int):
        pubs = await self._kv_json_list("governor:public_channels_json")
        pubs = [x for x in pubs if x != ch_id]
        await self._kv_set_json_list("governor:public_channels_json", pubs)
    async def _get_senior_total(self) -> int:
        raw = await self.us.get("xp:bot:senior_total") or "0"
        try: return int(str(raw).strip())
        except Exception:
            try:
                import json as _json
                return int(_json.loads(raw).get("senior_total_xp", 0))
            except Exception:
                return 0
    def _is_admin(self, ctx) -> bool:
        try:
            if ctx.author and ctx.author.id in self.admin_ids: return True
            perms = ctx.author.guild_permissions
            return perms.administrator or perms.manage_guild
        except Exception:
            return False
    def _looks_like_qna(self, content: str) -> bool:
        if not content: return False
        if _QNA_HEUR.search(content): return True
        if _LEINA_HEUR.search(content): return True
        return True
    async def _send_guard(self, channel_id: int, content: str) -> bool:
        locked, req, ok, public, pubs = await self.get_state()
        if channel_id == self.learn_ch:
            return True
        if locked:
            return False
        return channel_id in set(pubs)
    def _install_patch(self):
        if self._patch_done: return
        try:
            import discord.abc as _abc
            _orig_send = _abc.Messageable.send
        except Exception as e:
            log.warning("[governor] cannot locate Messageable.send: %r", e)
            return
        gate = self
        async def _wrapped_send(self, *args, **kwargs):
            content = kwargs.get("content", None)
            if len(args) >= 1 and content is None:
                content = args[0]
            try:
                ch_id = getattr(self, "id", None) or getattr(getattr(self, "channel", None), "id", None)
            except Exception:
                ch_id = None
            try:
                if await gate._send_guard(ch_id or 0, content if isinstance(content, str) else None):
                    return await _orig_send(self, *args, **kwargs)
                else:
                    log.info("[governor] suppress send in channel=%s (policy)", ch_id)
                    class _Dummy: id = None
                    return _Dummy()
            except Exception as e:
                log.warning("[governor] guard error: %r (fail-open)", e)
                return await _orig_send(self, *args, **kwargs)
        _abc.Messageable.send = _wrapped_send
        self._patch_done = True
        log.info("[governor] speak-policy patch installed")
    @commands.group(name="gate", invoke_without_command=True)
    async def gate_group(self, ctx):
        if not self._is_admin(ctx):
            return await ctx.reply("❌ kamu tidak punya izin.", mention_author=False)
        self._install_patch()
        locked, req, ok, public, pubs = await self.get_state()
        st = f"🔐 locked={locked} | interview_required={req} | interview_passed={ok} | public={public} | learn_ch={self.learn_ch} | pub_ch={pubs}"
        await ctx.reply(st, mention_author=False)
    @gate_group.command(name="status")
    async def gate_status(self, ctx):
        await self.gate_group.invoke(ctx)
    @gate_group.command(name="lock")
    async def gate_lock(self, ctx):
        if not self._is_admin(ctx):
            return await ctx.reply("❌", mention_author=False)
        await self.set_public_enabled(False)
        await self.set_gate_locked(True)
        self._install_patch()
        await ctx.reply("🔒 Gate locked (quarantine). QnA tetap belajar, balas hanya di LEARN channel.", mention_author=False)
    @gate_group.command(name="unlock")
    async def gate_unlock(self, ctx):
        if not self._is_admin(ctx):
            return await ctx.reply("❌", mention_author=False)
        locked, req, ok, public, pubs = await self.get_state()
        if req and not ok:
            return await ctx.reply("⚠️ Interview belum lulus.", mention_author=False)
        senior = await self._get_senior_total()
        if senior < self.senior_threshold:
            return await ctx.reply(f"⚠️ Senior XP belum cukup ({senior} < {self.senior_threshold}).", mention_author=False)
        await self.set_gate_locked(False)
        self._install_patch()
        await ctx.reply("✅ Gate unlocked (masih private). Gunakan `!go public` untuk tambah channel publik.", mention_author=False)
    @commands.group(name="go", invoke_without_command=True)
    async def go_group(self, ctx):
        if not self._is_admin(ctx):
            return await ctx.reply("❌", mention_author=False)
        await ctx.reply("Usage: `!go public [channel_id]` | `!go revoke [channel_id]` | `!go list`", mention_author=False)
    @go_group.command(name="public")
    async def go_public(self, ctx):
        if not self._is_admin(ctx):
            return await ctx.reply("❌", mention_author=False)
        parts = ctx.message.content.strip().split()
        target = None
        if len(parts) >= 3:
            try: target = int(parts[2])
            except Exception: target = None
        if target is None:
            target = self.public_ch_default
        await self.add_public_channel(target)
        await self.set_public_enabled(True)
        self._install_patch()
        await ctx.reply(f"🌐 Public channel ditambahkan: `{target}`. (Pastikan QNA_CHANNEL_ALLOWLIST mencakupnya).", mention_author=False)
    @go_group.command(name="revoke")
    async def go_revoke(self, ctx):
        if not self._is_admin(ctx):
            return await ctx.reply("❌", mention_author=False)
        parts = ctx.message.content.strip().split()
        if len(parts) < 3:
            return await ctx.reply("Gunakan: `!go revoke [channel_id]`", mention_author=False)
        try:
            target = int(parts[2])
        except Exception:
            return await ctx.reply("channel_id tidak valid.", mention_author=False)
        await self.remove_public_channel(target)
        await ctx.reply(f"🚫 Public channel dicabut: `{target}`.", mention_author=False)
    @go_group.command(name="list")
    async def go_list(self, ctx):
        if not self._is_admin(ctx):
            return await ctx.reply("❌", mention_author=False)
        _,_,_, public, pubs = await self.get_state()
        await ctx.reply(f"📜 Public channels: {pubs}", mention_author=False)
async def setup(bot):
    cog = GovernorGate(bot)
    await bot.add_cog(cog)
    cog._install_patch()
    log.info("[governor] speak-policy overlay v3 loaded")

def setup(bot):
    try:
        import asyncio
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            pass
        if loop and loop.is_running():
            return loop.create_task(setup(bot))
        else:
            return asyncio.run(setup(bot))
    except Exception:
        return None