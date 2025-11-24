# -*- coding: utf-8 -*-
"""
AutoLists Cog (FINAL)
=====================
Fokus:
- Tidak menyentuh ban/testban/webui.
- User cukup MENULIS domain di thread yang namanya mengandung "whitelist" / "blacklist".
- Menyimpan daftar ke:
    * data/whitelist_domains.json (list[str])
    * data/blacklist_domains.json (list[str])
    * data/url_whitelist.json     {"allow":[...]}
    * data/url_blocklist.json     {"domains":[...]}
    * whitelist.txt / blacklist.txt (mirror teks, 1 domain per baris)
- Membuat/menjaga thread "#log-botphising" → "memory W*B":
    * Embed ringkasan (pinned)
    * Pesan berisi lampiran whitelist.txt & blacklist.txt (mirror)
- Opsional commit ke GitHub (agar tidak reset saat redeploy):
    * AUTO_LISTS_GH_SYNC=1
    * GITHUB_TOKEN=<PAT>
    * GITHUB_REPO=owner/repo (mis. yuinaz/discord-bot-railway)
    * GITHUB_BRANCH=main  (default main)
    * Path override opsional (lihat variabel ENV di bawah).
"""
from __future__ import annotations

from discord.ext import commands

import os, re, json, asyncio
from pathlib import Path
from typing import List, Set, Optional, Dict

import discord

from ..helpers import lists_loader
from ..helpers import memory_wb

try:
    from ..helpers import github_sync
except Exception:
    github_sync = None  # type: ignore

DOMAIN_RE = re.compile(r"(?:^|\\s)([a-z0-9-]+(?:\\.[a-z0-9-]+)+)(?:\\s|$)", re.IGNORECASE)

def _env_path(key: str, default: str) -> Path:
    from os import getenv
    return Path(getenv(key, default))

# JSON local
WL_FILE = _env_path("WHITELIST_DOMAINS_FILE", "data/whitelist_domains.json")
BL_FILE = _env_path("BLACKLIST_DOMAINS_FILE", "data/blacklist_domains.json")
URL_WL_JSON = _env_path("URL_WHITELIST_JSON_FILE", "data/url_whitelist.json")
URL_BL_JSON = _env_path("URL_BLOCKLIST_JSON_FILE", "data/url_blocklist.json")

# TXT mirror local
WL_TXT = _env_path("WHITELIST_TXT_FILE", "whitelist.txt")
BL_TXT = _env_path("BLACKLIST_TXT_FILE", "blacklist.txt")

# Optional GitHub commit paths (in repo)
GH_WL_JSON_PATH = os.getenv("GITHUB_WHITELIST_JSON_PATH", "data/whitelist_domains.json")
GH_BL_JSON_PATH = os.getenv("GITHUB_BLACKLIST_JSON_PATH", "data/blacklist_domains.json")
GH_URL_WL_JSON_PATH = os.getenv("GITHUB_URL_WL_JSON_PATH", "data/url_whitelist.json")
GH_URL_BL_JSON_PATH = os.getenv("GITHUB_URL_BL_JSON_PATH", "data/url_blocklist.json")
GH_WL_TXT_PATH = os.getenv("GITHUB_WHITELIST_TXT_PATH", "whitelist.txt")
GH_BL_TXT_PATH = os.getenv("GITHUB_BLACKLIST_TXT_PATH", "blacklist.txt")

AUTO_GH_SYNC = os.getenv("AUTO_LISTS_GH_SYNC", "0") == "1"
LOG_CHANNEL_NAME = os.getenv("LOG_CHANNEL_NAME", "log-botphising")

def ensure_data_dir():
    for p in (WL_FILE, BL_FILE, URL_WL_JSON, URL_BL_JSON, WL_TXT, BL_TXT):
        p.parent.mkdir(parents=True, exist_ok=True)

def _normalize_domain(d: str) -> str:
    d = d.strip().lower().lstrip(".")
    d = re.sub(r"^https?://", "", d)
    d = d.split("/")[0]
    return d if "." in d else ""

def extract_domains_from_text(text: str) -> List[str]:
    return [n for n in {_normalize_domain(m.group(1)) for m in DOMAIN_RE.finditer(text or "")} if n]

async def read_domains_from_attachments(attachments: List[discord.Attachment]) -> List[str]:
    out: List[str] = []
    for a in attachments or []:
        name = (a.filename or "").lower()
        try:
            content = await a.read()
        except Exception:
            continue
        if name.endswith(".txt"):
            for line in content.decode("utf-8", errors="ignore").splitlines():
                n = _normalize_domain(line)
                if n: out.append(n)
        elif name.endswith(".json"):
            try:
                data = json.loads(content.decode("utf-8", errors="ignore"))
            except Exception:
                data = None
            if isinstance(data, list):
                for x in data:
                    n = _normalize_domain(str(x)); 
                    if n: out.append(n)
            elif isinstance(data, dict):
                for key in ("allow","domains"):
                    if key in data and isinstance(data[key], list):
                        for x in data[key]:
                            n = _normalize_domain(str(x)); 
                            if n: out.append(n)
    return out

def _write_local_all_formats(wl: Set[str], bl: Set[str]) -> None:
    ensure_data_dir()
    wl_sorted = sorted(wl); bl_sorted = sorted(bl)
    # JSON list
    WL_FILE.write_text(json.dumps(wl_sorted, ensure_ascii=False, indent=2), encoding="utf-8")
    BL_FILE.write_text(json.dumps(bl_sorted, ensure_ascii=False, indent=2), encoding="utf-8")
    # JSON legacy
    URL_WL_JSON.write_text(json.dumps({"allow": wl_sorted}, ensure_ascii=False, indent=2), encoding="utf-8")
    URL_BL_JSON.write_text(json.dumps({"domains": bl_sorted}, ensure_ascii=False, indent=2), encoding="utf-8")
    # TXT mirror
    WL_TXT.write_text("\\n".join(wl_sorted) + ("\\n" if wl_sorted else ""), encoding="utf-8")
    BL_TXT.write_text("\\n".join(bl_sorted) + ("\\n" if bl_sorted else ""), encoding="utf-8")

def _github_sync(wl: Set[str], bl: Set[str]) -> None:
    if not (AUTO_GH_SYNC and github_sync is not None):
        return
    wl_sorted = sorted(wl); bl_sorted = sorted(bl)
    files: Dict[str, bytes] = {
        GH_WL_JSON_PATH: json.dumps(wl_sorted, ensure_ascii=False, indent=2).encode("utf-8"),
        GH_BL_JSON_PATH: json.dumps(bl_sorted, ensure_ascii=False, indent=2).encode("utf-8"),
        GH_URL_WL_JSON_PATH: json.dumps({"allow": wl_sorted}, ensure_ascii=False, indent=2).encode("utf-8"),
        GH_URL_BL_JSON_PATH: json.dumps({"domains": bl_sorted}, ensure_ascii=False, indent=2).encode("utf-8"),
        GH_WL_TXT_PATH: ("\\n".join(wl_sorted) + ("\\n" if wl_sorted else "")).encode("utf-8"),
        GH_BL_TXT_PATH: ("\\n".join(bl_sorted) + ("\\n" if bl_sorted else "")).encode("utf-8"),
    }
    try:
        github_sync.commit_files(files=files, message=f"auto_lists: update WL({len(wl_sorted)})/BL({len(bl_sorted)})")
    except Exception:
        # Jangan matikan bot bila commit gagal
        pass

class AutoLists(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._wl: Set[str] = set()
        self._bl: Set[str] = set()
        self._ready = asyncio.Event()

    @commands.Cog.listener()
    async def on_ready(self):
        data = lists_loader.load_whitelist_blacklist()
        self._wl = set(data.get("wl_domains", set()))
        self._bl = set(data.get("bl_domains", set()))
        self._ready.set()
        # Pastikan file lokal ada & update thread memory
        try:
            _ = lists_loader.save_lists(self._wl, set(), self._bl, set())
            _write_local_all_formats(self._wl, self._bl)
            await memory_wb.update_memory_wb(self.bot, self._wl, self._bl)
        except Exception:
            pass

    def _is_whitelist_thread(self, thread: Optional[discord.Thread]) -> bool:
        return bool(thread and "whitelist" in (thread.name or "").lower())

    def _is_blacklist_thread(self, thread: Optional[discord.Thread]) -> bool:
        return bool(thread and "blacklist" in (thread.name or "").lower())

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # --- PublicChatGate pre-send guard (auto-injected) ---
        gate = None
        try:
            gate = self.bot.get_cog("PublicChatGate")
        except Exception:
            pass
        try:
            if message.guild and gate and hasattr(gate, "should_allow_public_reply") and not gate.should_allow_public_reply(message):
                return
        except Exception:
            pass
        # --- end guard ---

        # THREAD/FORUM EXEMPTION — auto-inserted
        ch = getattr(message, "channel", None)
        if ch is not None:
            try:
                import discord
                # Exempt true Thread objects
                if isinstance(ch, getattr(discord, "Thread", tuple())):
                    return
                # Exempt thread-like channel types (public/private/news threads)
                ctype = getattr(ch, "type", None)
                if ctype in {
                    getattr(discord.ChannelType, "public_thread", None),
                    getattr(discord.ChannelType, "private_thread", None),
                    getattr(discord.ChannelType, "news_thread", None),
                }:
                    return
            except Exception:
                # If discord import/type checks fail, do not block normal flow
                pass
        if message.author.bot:
            return
        if not isinstance(message.channel, (discord.Thread,)):
            return

        thread: discord.Thread = message.channel  # type: ignore
        is_wl = self._is_whitelist_thread(thread)
        is_bl = self._is_blacklist_thread(thread)
        if not (is_wl or is_bl):
            return

        await self._ready.wait()

        domains = set(extract_domains_from_text(message.content or ""))
        domains |= set(await read_domains_from_attachments(list(message.attachments or [])))

        if not domains:
            return

        changed = False
        if is_wl:
            before = set(self._wl)
            self._wl |= domains
            self._bl -= domains
            changed = changed or (self._wl != before)
        elif is_bl:
            before = set(self._bl)
            self._bl |= domains
            self._wl -= domains
            changed = changed or (self._bl != before)

        if changed:
            try:
                # Simpan untuk kompatibilitas modul lain
                _ = lists_loader.save_lists(self._wl, set(), self._bl, set())
                # Tulis semua format lokal
                _write_local_all_formats(self._wl, self._bl)
                # Opsional commit ke GitHub
                _github_sync(self._wl, self._bl)
                # Update thread memory
                await memory_wb.update_memory_wb(self.bot, self._wl, self._bl)
            except Exception:
                pass

            try: await message.add_reaction("✅")
            except Exception: pass
            try:
                await message.reply(
                    f"Tersimpan: {', '.join(sorted(domains))} → WL={len(self._wl)} / BL={len(self._bl)}",
                    suppress=True, mention_author=False
                )
            except Exception:
                pass
async def setup(bot: commands.Bot):
    await bot.add_cog(AutoLists(bot))
def setup_old(bot: commands.Bot):
    bot.add_cog(AutoLists(bot))