from __future__ import annotations

from discord.ext import commands

import io, json, time, asyncio
from datetime import timedelta
from pathlib import Path
from typing import Optional, Dict

import discord

from ..helpers.score_utils import extract_text_ocr, extract_urls, is_bad_url, simple_bytes_hash, contains_phish_keywords

try:
    from PIL import Image
    import imagehash
except Exception:
    Image = None
    imagehash = None

DATA_DIR = Path(__file__).parents[2] / "data" / "anti_image"
DATA_DIR.mkdir(parents=True, exist_ok=True)
WL_FILE = DATA_DIR / "image_whitelist.json"
if not WL_FILE.exists():
    WL_FILE.write_text(json.dumps({"images": [], "channels": []}, indent=2), encoding="utf-8")

DEFAULT_CFG = {
    "timeout_minutes": 20,
    "burst_window_seconds": 60,
    "burst_min_msgs": 3,
    "skip_roles": ["Owner","Admin","Moderator"],
    "log_channel_name": "log-botphising",
    "fp_thread_name": "imagephising-fp-log",
    "read_thread_name": "imagephising",
    "read_backfill_limit": 1000,
    "protected_thread_names": ["imagephising","whitelist","blacklist","ban log","ban-log","banlog"]
}

def load_wl() -> dict:
    try:
        return json.loads(WL_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"images": [], "channels": []}

def save_wl(d: dict) -> None:
    try:
        WL_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

class AntiImageScoredGuard(commands.Cog):
    """Armed High-Confidence guard: read-only scan existing 'imagephising', log to NEW FP thread.
    Hotfix: no create_task at import, bootstrap on on_ready; use datetime.timedelta.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cfg = DEFAULT_CFG.copy()
        self.wl = load_wl()
        self._recent_msgs: Dict[int, list[float]] = {}
        self._fp_thread_id_by_guild: Dict[int, int] = {}
        self._booted = False  # ensure one-time bootstrap

    @commands.Cog.listener()
    async def on_ready(self):
        if self._booted:
            return
        self._booted = True
        try:
            for guild in self.bot.guilds:
                await self._ensure_fp_thread(guild)
                await self._readonly_scan_imagephising(guild)
        except Exception:
            pass

    async def _readonly_scan_imagephising(self, guild: discord.Guild):
        target = self.cfg["read_thread_name"].lower()
        try:
            for ch in guild.text_channels:
                for th in ch.threads:
                    if th.name.lower() == target:
                        await self._scan_thread_to_whitelist(th); return
                try:
                    async for th in ch.archived_threads(limit=50, private=False):
                        if th.name.lower() == target:
                            await self._scan_thread_to_whitelist(th); return
                except Exception:
                    pass
        except Exception:
            pass

    async def _scan_thread_to_whitelist(self, thread: discord.Thread):
        limit = int(self.cfg["read_backfill_limit"])
        added = 0
        try:
            async for msg in thread.history(limit=limit, oldest_first=True):
                for a in getattr(msg, "attachments", []) or []:
                    if (a.content_type or "").startswith("image/"):
                        try:
                            b = await a.read()
                        except Exception:
                            continue
                        sha1 = simple_bytes_hash(b)
                        d = self.wl
                        imgs = set(d.get("images", []))
                        if sha1 not in imgs:
                            imgs.add(sha1); d["images"] = sorted(imgs); save_wl(d); self.wl = d; added += 1
        except Exception:
            pass
        # No posting to this thread.

    async def _ensure_fp_thread(self, guild: discord.Guild):
        fp_name = self.cfg["fp_thread_name"].lower()
        parent = None
        for ch in guild.text_channels:
            if ch.name == self.cfg["log_channel_name"]:
                parent = ch; break
        if parent is None:
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    parent = ch; break
        if parent is None:
            return
        found = None
        try:
            for th in parent.threads:
                if th.name.lower() == fp_name:
                    found = th; break
            if not found:
                async for th in parent.archived_threads(limit=50, private=False):
                    if th.name.lower() == fp_name:
                        found = th; break
        except Exception:
            pass
        if found is None:
            try:
                if parent.permissions_for(guild.me).create_public_threads:
                    found = await parent.create_thread(name=self.cfg["fp_thread_name"], auto_archive_duration=10080)
            except Exception:
                pass
        if found:
            self._fp_thread_id_by_guild[guild.id] = found.id

    def _skipped_role(self, member: discord.Member) -> bool:
        names = {r.name for r in getattr(member, "roles", [])}
        return any(s in names for s in self.cfg["skip_roles"])

    def _signals(self, b: bytes, message: discord.Message) -> Dict[str, bool]:
        sig = {"kw": False, "url": False, "burst": False, "young": False, "wl_img": False, "wl_chan_protected": False}
        sha1 = simple_bytes_hash(b)
        if sha1 in set(self.wl.get("images", [])):
            sig["wl_img"] = True

        txt = extract_text_ocr(b)
        if txt and contains_phish_keywords(txt):
            sig["kw"] = True

        urls = extract_urls(message.content or "")
        if urls and any(is_bad_url(u) for u in urls):
            sig["url"] = True

        now = time.time()
        arr = self._recent_msgs.setdefault(message.author.id, [])
        arr.append(now)
        arr[:] = [t for t in arr if now - t <= self.cfg["burst_window_seconds"]]
        if len(arr) >= self.cfg["burst_min_msgs"]:
            sig["burst"] = True

        try:
            if isinstance(message.author, discord.Member):
                if (now - message.author.created_at.timestamp()) < 7*24*3600:
                    sig["young"] = True
        except Exception:
            pass

        try:
            ch_name = getattr(message.channel, "name", "") or ""
            if ch_name.lower() in [n.lower() for n in self.cfg["protected_thread_names"]]:
                sig["wl_chan_protected"] = True
        except Exception:
            pass

        return sig

    def _fp_thread(self, guild: discord.Guild) -> Optional[discord.Thread]:
        tid = self._fp_thread_id_by_guild.get(guild.id)
        if not tid: return None
        try: return guild.get_thread(tid) or None
        except Exception: return None

    async def _send_to_fp_thread(self, guild: discord.Guild, embed: discord.Embed, view: Optional[discord.ui.View]=None):
        th = self._fp_thread(guild)
        if th:
            try:
                await th.send(embed=embed, view=view, silent=True); return
            except Exception:
                pass
        for ch in guild.text_channels:
            if ch.name == self.cfg["log_channel_name"] and ch.permissions_for(guild.me).send_messages:
                try: await ch.send(embed=embed, view=view, silent=True)
                except Exception: pass
                return

    @commands.Cog.listener("on_message")
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
        if message.author.bot or not message.attachments:
            return
        if not isinstance(message.channel, (discord.TextChannel, discord.Thread)):
            return
        if isinstance(message.author, discord.Member) and self._skipped_role(message.author):
            return

        img_attachments = [a for a in message.attachments if (a.content_type or "").startswith("image/")]
        if not img_attachments: return

        try:
            b = await img_attachments[0].read()
        except Exception:
            return

        sig = self._signals(b, message)

        desc = f"signals: `kw={int(sig['kw'])}, url={int(sig['url'])}, burst={int(sig['burst'])}, young={int(sig['young'])}`"
        if sig["wl_chan_protected"]:
            desc += " • channel=protected(log-only)"
        e = discord.Embed(
            title="Anti-Image Guard (armed-high)",
            description=f"{desc}\nAuthor: {message.author.mention} • Channel: {getattr(message.channel,'mention','#?')}",
            color=discord.Color.orange()
        )
        try: e.set_image(url=img_attachments[0].url)
        except: pass

        if sig["wl_chan_protected"] or sig["wl_img"]:
            await self._send_to_fp_thread(message.guild, e, self._make_view(b, message))
            return

        high_conf = (sig["url"] and sig["kw"]) or (sig["url"] and (sig["burst"] or sig["young"])) or (sig["kw"] and (sig["burst"] or sig["young"]))
        medium = (sig["url"] or sig["kw"]) and not high_conf

        if high_conf:
            await self._do_ban(message, e, self._make_view(b, message))
        elif medium:
            await self._do_quarantine(message, e, self._make_view(b, message))
        else:
            await self._send_to_fp_thread(message.guild, e, self._make_view(b, message))

    def _make_view(self, img_bytes: bytes, message: discord.Message) -> discord.ui.View:
        sha1 = simple_bytes_hash(img_bytes)
        outer = self
        class V(discord.ui.View):
            def __init__(self): super().__init__(timeout=600)
            async def _allowed(self, it: discord.Interaction) -> bool:
                if not isinstance(it.user, discord.Member): return False
                p = it.user.guild_permissions
                return p.manage_messages or p.kick_members or p.ban_members
            @discord.ui.button(label="Approve (Whitelist)", style=discord.ButtonStyle.success)
            async def approve(self, it: discord.Interaction, _):
                if not await self._allowed(it):
                    await it.response.send_message("Moderator only.", ephemeral=True); return
                d = outer.wl; arr = set(d.get("images", [])); arr.add(sha1); d["images"] = sorted(arr); save_wl(d); outer.wl = d
                await it.response.send_message("Ditambahkan ke whitelist.", ephemeral=True)
            @discord.ui.button(label="Ban + delete 7d", style=discord.ButtonStyle.danger)
            async def ban(self, it: discord.Interaction, _):
                if not await self._allowed(it):
                    await it.response.send_message("Moderator only.", ephemeral=True); return
                try:
                    await message.author.ban(reason="Anti-Image Guard (armed)", delete_message_days=7)
                    await it.response.send_message("User diban & pesan 7 hari dihapus.", ephemeral=True)
                except Exception as e:
                    await it.response.send_message(f"Gagal ban: {e}", ephemeral=True)
        return V()

    async def _do_ban(self, message: discord.Message, embed: discord.Embed, view: discord.ui.View):
        try: await message.delete()
        except: pass
        try:
            await message.author.ban(reason="Anti-Image Guard (armed)", delete_message_days=7)
        except: pass
        await self._send_to_fp_thread(message.guild, embed, view)

    async def _do_quarantine(self, message: discord.Message, embed: discord.Embed, view: discord.ui.View):
        try: await message.delete()
        except: pass
        try:
            until = discord.utils.utcnow() + timedelta(minutes=int(DEFAULT_CFG["timeout_minutes"]))
            await message.author.edit(communication_disabled_until=until)
        except: pass
        await self._send_to_fp_thread(message.guild, embed, view)
async def setup(bot: commands.Bot):
    await bot.add_cog(AntiImageScoredGuard(bot))