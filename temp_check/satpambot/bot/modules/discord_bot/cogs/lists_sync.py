from __future__ import annotations

from discord.ext import commands

import asyncio, os, re, json, logging
from typing import Optional, List, Tuple
import discord

from satpambot.bot.modules.discord_bot.helpers import lists_loader, modlog, github_sync

log = logging.getLogger(__name__)

def _env(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or "").strip()

def _env_bool(name: str, default: bool=False) -> bool:
    v = _env(name, "1" if default else "")
    return v.lower() in ("1","true","yes","on")

LISTS_WHITELIST_THREAD_NAME = _env("LISTS_WHITELIST_THREAD_NAME", "whitelist")
LISTS_BLACKLIST_THREAD_NAME = _env("LISTS_BLACKLIST_THREAD_NAME", "blacklist")
LISTS_GITHUB_REPO = _env("GITHUB_REPO", "")
LISTS_GITHUB_BRANCH = _env("GITHUB_BRANCH", "main")
LISTS_GITHUB_PATH_WL = _env("GITHUB_PATH_WHITELIST_JSON", "satpambot/data/whitelist.json")
LISTS_GITHUB_PATH_BL = _env("GITHUB_PATH_BLACKLIST_JSON", "satpambot/data/blacklist.json")
LISTS_GITHUB_ENABLED = _env_bool("GITHUB_SYNC_ENABLED", True)

class ListsSync(commands.Cog):

    def _extract_domains_from_text(self, text: str):
        # Extract raw domains and domains from URLs
        doms = set()
        if not text:
            return doms
        # from URLs
        for m in re.finditer(r"https?://([^/\s:]+)", text, re.IGNORECASE):
            doms.add(m.group(1).lower())
        # bare domains
        for m in re.finditer(r"\b([a-z0-9-]+(?:\.[a-z0-9-]+)+)\b", text, re.IGNORECASE):
            doms.add(m.group(1).lower())
        # strip common trailing punctuation
        cleaned = set()
        for d in doms:
            cleaned.add(d.strip(".,;:!?)(").lower())
        return cleaned

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._wh_thread_id: Optional[int] = None
        self._bl_thread_id: Optional[int] = None
        self._lock = asyncio.Lock()

    async def _ensure_threads(self, guild: discord.Guild):
        ch = await modlog.resolve_log_channel(guild)
        if not ch:
            return
        # Try find existing threads by name
        for th in getattr(ch, "threads", []) or []:
            n = (getattr(th, "name","") or "").lower()
            if n == LISTS_WHITELIST_THREAD_NAME.lower():
                self._wh_thread_id = th.id
            elif n == LISTS_BLACKLIST_THREAD_NAME.lower():
                self._bl_thread_id = th.id
        # Create if missing
        if not self._wh_thread_id:
            try:
                th = await ch.create_thread(name=LISTS_WHITELIST_THREAD_NAME, auto_archive_duration=10080)
                self._wh_thread_id = th.id
                await th.send("📜 Thread ini dipakai untuk **WHITELIST**. Kirim `.json` / `.txt` atau gunakan perintah:\n`!wl add <domain|regex>` / `!wl del <domain|regex>` / `!wl show`")
            except Exception as e:
                log.debug("create whitelist thread failed: %s", e)
        if not self._bl_thread_id:
            try:
                th = await ch.create_thread(name=LISTS_BLACKLIST_THREAD_NAME, auto_archive_duration=10080)
                self._bl_thread_id = th.id
                await th.send("⛔ Thread ini dipakai untuk **BLACKLIST**. Kirim `.json` / `.txt` atau gunakan perintah:\n`!bl add <domain|regex>` / `!bl del <domain|regex>` / `!bl show`")
            except Exception as e:
                log.debug("create blacklist thread failed: %s", e)

    @commands.Cog.listener()
    async def on_ready(self):
        # ensure threads for all guilds
        for g in self.bot.guilds:
            await self._ensure_threads(g)

    def _parse_lines(self, text: str) -> List[str]:
        out = []
        for line in (text or "").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            out.append(line)
        return out

    async def _update_and_broadcast(self, guild: discord.Guild, wl_domains, wl_patterns, bl_domains, bl_patterns, source: str):
        # Save locally
        ok = lists_loader.save_lists(wl_domains, wl_patterns, bl_domains, bl_patterns)
        # GitHub sync
        if LISTS_GITHUB_ENABLED and LISTS_GITHUB_REPO:
            try:
                client = github_sync.GitHubClient()
                wl_bytes = json.dumps({"domains": sorted(set(wl_domains)), "patterns": wl_patterns}, ensure_ascii=False, indent=2).encode("utf-8")
                bl_bytes = json.dumps({"domains": sorted(set(bl_domains)), "patterns": bl_patterns}, ensure_ascii=False, indent=2).encode("utf-8")
                cmt = f"lists_sync: update from Discord ({source})"
                await client.put_file(LISTS_GITHUB_REPO, LISTS_GITHUB_PATH_WL, wl_bytes, cmt, LISTS_GITHUB_BRANCH)
                await client.put_file(LISTS_GITHUB_REPO, LISTS_GITHUB_PATH_BL, bl_bytes, cmt, LISTS_GITHUB_BRANCH)
            except Exception as e:
                await modlog.send_error(guild, content=f"GitHub sync gagal: {e}")
        # Reload to cogs
        new_lists = lists_loader.load_whitelist_blacklist()
        for cog in self.bot.cogs.values():
            try:
                if hasattr(cog, "_apply_lists"):
                    cog._apply_lists(new_lists)
            except Exception:
                pass
        # Log
        from discord import Embed, Colour
        emb = Embed(title="✅ Lists updated", colour=Colour.green(), description=f"Source: {source}")
        emb.add_field(name="Whitelist domains", value=str(len(wl_domains)))
        emb.add_field(name="Whitelist patterns", value=str(len(wl_patterns)))
        emb.add_field(name="Blacklist domains", value=str(len(bl_domains)))
        emb.add_field(name="Blacklist patterns", value=str(len(bl_patterns)))
        await modlog.send_embed(guild, emb)

    async def _handle_command(self, message: discord.Message, which: str, cmd: str, arg: str):
        lists = lists_loader.load_whitelist_blacklist()
        wl_domains = set(lists["wl_domains"]); wl_patterns = lists["wl_patterns"]
        bl_domains = set(lists["bl_domains"]); bl_patterns = lists["bl_patterns"]
        changed = False

        if cmd == "show":
            from discord import Embed, Colour
            emb = Embed(title=f"{which.upper()} snapshot", colour=Colour.blurple())
            if which == "wl":
                emb.add_field(name="domains", value=str(len(wl_domains)))
                emb.add_field(name="patterns", value=str(len(wl_patterns)))
            else:
                emb.add_field(name="domains", value=str(len(bl_domains)))
                emb.add_field(name="patterns", value=str(len(bl_patterns)))
            await message.reply(embed=emb, mention_author=False)
            return

        if cmd in ("add","del") and not arg:
            await message.reply(f"Format: `!{which} {cmd} <domain|regex>`", mention_author=False)
            return

        if which == "wl":
            if cmd == "add":
                if re.search(r"[a-z0-9-]+\.[a-z]{2,}", arg.lower()):
                    wl_domains.add(arg.lower().strip())
                else:
                    wl_patterns = wl_patterns + [arg]
                changed = True
            elif cmd == "del":
                try:
                    wl_domains.discard(arg.lower().strip())
                    wl_patterns = [p for p in wl_patterns if p != arg]
                    changed = True
                except Exception:
                    pass
        else:
            if cmd == "add":
                if re.search(r"[a-z0-9-]+\.[a-z]{2,}", arg.lower()):
                    bl_domains.add(arg.lower().strip())
                else:
                    bl_patterns = bl_patterns + [arg]
                changed = True
            elif cmd == "del":
                try:
                    bl_domains.discard(arg.lower().strip())
                    bl_patterns = [p for p in bl_patterns if p != arg]
                    changed = True
                except Exception:
                    pass

        if changed:
            async with self._lock:
                await self._update_and_broadcast(message.guild, wl_domains, wl_patterns, bl_domains, bl_patterns, f"command {which} {cmd}")
            await message.add_reaction("✅")

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
        if message.author.bot or not message.guild:
            return
        # Only handle threads in log channel
        ch = await modlog.resolve_log_channel(message.guild)
        if not ch:
            return
        in_wl = bool(self._wh_thread_id and message.channel.id == self._wh_thread_id)
        in_bl = bool(self._bl_thread_id and message.channel.id == self._bl_thread_id)
        if not (in_wl or in_bl):
            return

        # Commands: !wl add/del/show , !bl add/del/show
        m = re.match(r"!(wl|bl)\s+(add|del|show)\s*(.*)", (message.content or "").strip(), re.IGNORECASE)
        if m:
            which, cmd, arg = m.group(1).lower(), m.group(2).lower(), m.group(3).strip()
            await self._handle_command(message, which, cmd, arg)
            return


        # Auto-add domains from plain text (no commands needed)
        if (in_wl or in_bl) and (message.content or "").strip():
            domains = self._extract_domains_from_text(message.content or "")
            if domains:
                lists = lists_loader.load_whitelist_blacklist()
                wl_domains = set(lists["wl_domains"]); wl_patterns = lists["wl_patterns"]
                bl_domains = set(lists["bl_domains"]); bl_patterns = lists["bl_patterns"]
                if in_wl:
                    new_items = [d for d in domains if d not in wl_domains]
                    if new_items:
                        wl_domains |= set(new_items)
                        async with self._lock:
                            await self._update_and_broadcast(message.guild, wl_domains, wl_patterns, bl_domains, bl_patterns, "auto-wl text")
                        await message.add_reaction("✅")
                elif in_bl:
                    new_items = [d for d in domains if d not in bl_domains]
                    if new_items:
                        bl_domains |= set(new_items)
                        async with self._lock:
                            await self._update_and_broadcast(message.guild, wl_domains, wl_patterns, bl_domains, bl_patterns, "auto-bl text")
                        await message.add_reaction("✅")
            # continue to handle attachments after (if any)
        
        # Attachments: .txt or .json -> replace respective list
        if message.attachments:
            for a in message.attachments:
                name = (a.filename or "").lower()
                if not (name.endswith(".txt") or name.endswith(".json")):
                    continue
                try:
                    data = await a.read()
                    if name.endswith(".json"):
                        payload = json.loads(data.decode("utf-8", errors="ignore"))
                        dom = payload.get("domains") or []
                        pat = payload.get("patterns") or []
                    else:
                        # text -> split lines into domains+patterns heuristically
                        lines = self._parse_lines(data.decode("utf-8", errors="ignore"))
                        dom = []; pat = []
                        for s in lines:
                            if re.search(r"[a-z0-9-]+\.[a-z]{2,}", s.lower()):
                                dom.append(s.lower())
                            else:
                                pat.append(s)
                    lists = lists_loader.load_whitelist_blacklist()
                    wl_domains = set(lists["wl_domains"]); wl_patterns = lists["wl_patterns"]
                    bl_domains = set(lists["bl_domains"]); bl_patterns = lists["bl_patterns"]
                    if in_wl:
                        wl_domains = set(dom); wl_patterns = pat
                        src = f"upload whitelist {name}"
                    else:
                        bl_domains = set(dom); bl_patterns = pat
                        src = f"upload blacklist {name}"
                    async with self._lock:
                        await self._update_and_broadcast(message.guild, wl_domains, wl_patterns, bl_domains, bl_patterns, src)
                    await message.add_reaction("✅")
                except Exception as e:
                    await modlog.send_error(message.guild, content=f"Parse attachment gagal: {e}")
async def setup(bot: commands.Bot):
    await bot.add_cog(ListsSync(bot))