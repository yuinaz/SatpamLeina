from __future__ import annotations

from discord.ext import commands

import asyncio, json, time, os
from datetime import timedelta
from pathlib import Path
from typing import Dict, Optional, Set, DefaultDict, List, Tuple
from collections import defaultdict
import discord

from discord import app_commands

CFG_PATH = Path("config") / "auto_role_anywhere.json"
STATE_PATH = Path("data") / "autorole_state.json"
MARKER_PREFIX = "[satpambot:auto_prune_state]"

def _env_int(name: str, default: int = 0) -> int:
    try: return int(os.getenv(name, str(default)).strip())
    except Exception: return default

DEFAULT_CFG = {
    "text_channels": {},
    "threads": {},
    "thread_join_cooldown_s": 3600,
    "grant_on_thread_member_join": False,
    "backfill_default_limit": 800,
    "prune_default_days": 90,
    "prune_sleep_ms_per_action": 300,
    "prune_pause_ms_between_channels": 800,
    "prune_max_actions_per_run": 150,
    "restrict_to_role_ids": [],
    "prune_include_threads": False,
    "prune_exempt_role_ids": [],

    # Auto scheduler
    "auto_prune_enabled": True,
    "auto_prune_interval_hours": 24,
    "prune_use_deploy_grace": True,

    # Persist baseline across redeploys using Discord message
    # If not set, will fallback ke ENV LOG_CHANNEL_ID / LOG_CHANNEL_ID_RAW
    "state_marker_channel_id": 0,
    "state_marker_pin": False  # anti-spam: tidak perlu pin
}

def _to_int_map(d: Dict) -> Dict[int, int]:
    out: Dict[int, int] = {}
    if not isinstance(d, dict): return out
    for k, v in d.items():
        try:
            ki = int(k)
            vi = int(v if not isinstance(v, dict) else v.get("role"))
            out[ki] = vi
        except Exception:
            pass
    return out

def _now() -> float:
    return time.time()

class AutoRoleAnywhere(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cfg: Dict = dict(DEFAULT_CFG)
        self.text_map: Dict[int, int] = {}
        self.thread_map: Dict[int, int] = {}
        self.thread_name_map: Dict[str, int] = {}
        self.allowed_roles: Set[int] = set()
        self.exempt_roles: Set[int] = set()
        self.prune_include_threads: bool = False
        self._last_thread_join: DefaultDict[int, float] = defaultdict(lambda: 0.0)
        self._started = False
        self._task_auto = None
        self.state = {"deploy_epoch": None}

    # ---------- config/state ----------
    def _load_cfg(self):
        try:
            obj = json.loads(Path(CFG_PATH).read_text(encoding="utf-8"))
        except Exception:
            obj = {}
        self.cfg = {**DEFAULT_CFG, **(obj or {})}

        text_map = _to_int_map(self.cfg.get("text_channels", {}))
        text_map.update(_to_int_map(self.cfg.get("channel_id_map", {})))   # legacy

        thread_map = _to_int_map(self.cfg.get("threads", {}))
        thread_map.update(_to_int_map(self.cfg.get("thread_id_map", {})))   # legacy

        self.text_map = text_map
        self.thread_map = thread_map

        try:
            tn = self.cfg.get("thread_name_map", {}) or {}
            self.thread_name_map = {
                str(name): int(val["role"] if isinstance(val, dict) else int(val))
                for name, val in tn.items()
            }
        except Exception:
            self.thread_name_map = {}

        mapped_roles = set(list(self.text_map.values()) + list(self.thread_map.values()))
        extra = set(int(x) for x in (self.cfg.get("restrict_to_role_ids") or []) if str(x).isdigit())
        self.allowed_roles = (mapped_roles if not extra else (mapped_roles & extra)) or mapped_roles

        self.exempt_roles = set(int(x) for x in (self.cfg.get("prune_exempt_role_ids") or []) if str(x).isdigit())
        self.prune_include_threads = bool(self.cfg.get("prune_include_threads", False))

    def _load_state_local(self):
        try:
            STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            if STATE_PATH.exists():
                self.state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            else:
                self.state = {"deploy_epoch": None}
        except Exception:
            self.state = {"deploy_epoch": None}

    def _save_state_local(self):
        try:
            STATE_PATH.write_text(json.dumps(self.state), encoding="utf-8")
        except Exception:
            pass

    async def _ensure_baseline_persisted(self):
        """Pastikan deploy_epoch persist antar-redeploy dengan menyimpan/ambil dari Discord message."""
        # 1) load local (kalau ada)
        self._load_state_local()
        if self.state.get("deploy_epoch"):
            return  # sudah punya

        # 2) cari marker di channel
        marker_channel_id = int(self.cfg.get("state_marker_channel_id") or 0) or _env_int("LOG_CHANNEL_ID", _env_int("LOG_CHANNEL_ID_RAW", 0))
        if not marker_channel_id:
            # fallback: set baseline baru
            self.state["deploy_epoch"] = _now()
            self._save_state_local()
            return

        # cari channel di semua guild
        ch = None
        for g in self.bot.guilds:
            tmp = g.get_channel(marker_channel_id)
            if tmp:
                ch = tmp; break
        if not isinstance(ch, (discord.TextChannel, discord.Thread)):
            # fallback
            self.state["deploy_epoch"] = _now()
            self._save_state_local()
            return

        # 2a) cek pinned dulu
        deploy_epoch = None
        try:
            pins = await ch.pins()
            for m in pins:
                if m.author.bot and m.content.startswith(MARKER_PREFIX):
                    try:
                        j = json.loads(m.content[len(MARKER_PREFIX):].strip())
                        deploy_epoch = float(j.get("deploy_epoch"))
                        break
                    except Exception:
                        continue
        except Exception:
            pass

        # 2b) kalau belum ada, scan beberapa pesan terakhir (ringan)
        if deploy_epoch is None:
            try:
                async for m in ch.history(limit=200):
                    if m.author.bot and isinstance(m.content, str) and m.content.startswith(MARKER_PREFIX):
                        try:
                            j = json.loads(m.content[len(MARKER_PREFIX):].strip())
                            deploy_epoch = float(j.get("deploy_epoch"))
                            break
                        except Exception:
                            continue
            except Exception:
                pass

        # 3) jika ketemu, simpan lokal; jika tidak, tulis marker baru
        if deploy_epoch is not None and deploy_epoch > 0:
            self.state["deploy_epoch"] = deploy_epoch
            self._save_state_local()
            return

        # tulis marker baru dengan now()
        self.state["deploy_epoch"] = _now()
        self._save_state_local()
        try:
            msg = await ch.send(f"{MARKER_PREFIX} " + json.dumps({"deploy_epoch": self.state["deploy_epoch"]}))
            if bool(self.cfg.get("state_marker_pin", False)):
                try: await msg.pin()
                except Exception: pass
        except Exception:
            pass

    # ---------- helpers ----------
    def _mapped_role_for(self, channel_id: int) -> Optional[int]:
        if channel_id in self.text_map: return self.text_map[channel_id]
        if channel_id in self.thread_map: return self.thread_map[channel_id]
        return None

    def _cooldown_ok(self, thread_id: int) -> bool:
        now = _now()
        if now - self._last_thread_join[thread_id] < int(self.cfg.get("thread_join_cooldown_s", 3600)):
            return False
        self._last_thread_join[thread_id] = now
        return True

    async def _grant(self, member: discord.Member, role_id: int):
        if role_id not in self.allowed_roles: return
        role = member.guild.get_role(int(role_id))
        if not role: return
        if role in member.roles: return
        try:
            await member.add_roles(role, reason="autorole: chatted in mapped location")
        except Exception:
            pass

    async def _iter_recent_authors(self, ch: discord.abc.GuildChannel, limit: int, days_window: Optional[int] = None):
        seen: Set[int] = set()
        after = None
        if days_window:
            after = discord.utils.utcnow() - timedelta(days=int(days_window))
        history_kwargs = {"limit": int(limit)}
        if after: history_kwargs["after"] = after
        try:
            async for m in ch.history(**history_kwargs):
                a = getattr(m.author, "id", None)
                if a: seen.add(int(a))
                if len(seen) >= limit: break
        except Exception:
            pass
        return seen

    # ---------- events ----------
    @commands.Cog.listener()
    async def on_ready(self):
        if self._started: return
        self._started = True
        self._load_cfg()
        # pastikan baseline persist (scan/tulis marker di Discord)
        await self._ensure_baseline_persisted()

        # auto-prune loop (free-plan friendly: once per interval)
        if bool(self.cfg.get("auto_prune_enabled", True)):
            async def _auto_loop():
                await self.bot.wait_until_ready()
                while not self.bot.is_closed():
                    try:
                        await self._auto_prune_once()
                    except Exception:
                        pass
                    hours = max(1, int(self.cfg.get("auto_prune_interval_hours", 24)))
                    await asyncio.sleep(hours * 3600)
            self._task_auto = asyncio.create_task(_auto_loop())

    @commands.Cog.listener()
    async def on_thread_member_join(self, member: discord.ThreadMember):
        if not bool(self.cfg.get("grant_on_thread_member_join", False)): return
        th = member.thread
        rid = self.thread_map.get(getattr(th, "id", 0))
        if rid and self._cooldown_ok(int(th.id)):
            try:
                await self._grant(member, int(rid))  # type: ignore
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        # THREAD/FORUM EXEMPTION — auto-inserted
        ch = getattr(msg, "channel", None)
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
        if not msg.guild or msg.author.bot: return
        if isinstance(msg.author, discord.Member):
            rid: Optional[int] = None
            if isinstance(msg.channel, discord.TextChannel):
                rid = self.text_map.get(msg.channel.id)
            elif isinstance(msg.channel, discord.Thread):
                rid = self.thread_map.get(msg.channel.id)
                # parent-fallback: forum/text parent → role
                if not rid:
                    parent = getattr(msg.channel, "parent", None)
                    if parent is not None:
                        rid = self.text_map.get(getattr(parent, "id", 0))
                # optional: name-based
                if not rid and self.thread_name_map:
                    name = (getattr(msg.channel, "name", "") or "")
                    if name in self.thread_name_map:
                        rid = int(self.thread_name_map[name])
            if rid:
                await self._grant(msg.author, int(rid))

    # ---------- auto prune core ----------
    async def _auto_prune_once(self):
        d = max(7, min(90, int(self.cfg.get("prune_default_days", 90))))
        if bool(self.cfg.get("prune_use_deploy_grace", True)):
            deploy_epoch = float(self.state.get("deploy_epoch") or _now())
            if (_now() - deploy_epoch) < d * 86400:
                return  # belum 90 hari sejak deploy → jangan prune dulu

        targets: List[Tuple[discord.abc.GuildChannel, int]] = []
        for g in list(self.bot.guilds):
            for cid, rid in self.text_map.items():
                if int(rid) in self.exempt_roles: continue
                ch = g.get_channel(cid)
                if isinstance(ch, discord.TextChannel):
                    targets.append((ch, rid))
            if bool(self.cfg.get("prune_include_threads", False)):
                for tid, rid in self.thread_map.items():
                    if int(rid) in self.exempt_roles: continue
                    th = g.get_thread(tid) or self.bot.get_channel(tid)
                    if isinstance(th, discord.Thread) and th.guild.id == g.id:
                        targets.append((th, rid))

        pause_ms = int(self.cfg.get("prune_pause_ms_between_channels", 800))
        sleep_ms = int(self.cfg.get("prune_sleep_ms_per_action", 300))
        cap = int(self.cfg.get("prune_max_actions_per_run", 150))
        removed = 0
        for ch, rid in targets:
            role = ch.guild.get_role(int(rid))
            if not role or int(role.id) in self.exempt_roles:
                await asyncio.sleep(max(50, pause_ms)/1000.0); 
                continue
            active = await self._iter_recent_authors(ch, 2000, days_window=d)
            for m in list(role.members):
                if removed >= cap: break
                if m.id in active: continue
                try:
                    await m.remove_roles(role, reason=f"autorole(auto): tidak aktif {d} hari")
                    removed += 1
                except Exception:
                    pass
                await asyncio.sleep(max(100, sleep_ms)/1000.0)
            await asyncio.sleep(max(50, pause_ms)/1000.0)

    # ---------- slash cmds ----------
    group = app_commands.Group(name="roleauto", description="Auto role (chatters only) + prune")

    @group.command(name="reload", description="Reload config/auto_role_anywhere.json")
    async def reload_cmd(self, itx: discord.Interaction):
        if not itx.user.guild_permissions.manage_guild:
            return await itx.response.send_message("Butuh izin Manage Server.", ephemeral=True)
        self._load_cfg()
        await itx.response.send_message("Autorole config reloaded ✅", ephemeral=True)

    @group.command(name="status", description="Lihat status auto-prune (grace deploy & interval)")
    async def status_cmd(self, itx: discord.Interaction):
        if not itx.user.guild_permissions.manage_guild:
            return await itx.response.send_message("Butuh izin Manage Server.", ephemeral=True)
        d = int(self.cfg.get("prune_default_days", 90))
        deploy_epoch = float(self.state.get("deploy_epoch") or 0.0)
        since = (time.time() - deploy_epoch) if deploy_epoch else 0.0
        remain = max(0, (d*86400) - since) if bool(self.cfg.get("prune_use_deploy_grace", True)) else 0
        hrs = max(1, int(self.cfg.get("auto_prune_interval_hours", 24)))
        txt = f"auto_prune_enabled={self.cfg.get('auto_prune_enabled', True)} • interval={hrs}h • grace_remaining_hours={int(remain/3600)}h"
        await itx.response.send_message(txt, ephemeral=True)

    @group.command(name="backfill", description="Kasih role ke author yang pernah chat di sini")
    @app_commands.describe(limit="Jumlah pesan terakhir utk discan (default config)")
    async def backfill_cmd(self, itx: discord.Interaction, limit: Optional[int] = None):
        if not itx.user.guild_permissions.manage_guild:
            return await itx.response.send_message("Butuh izin Manage Server.", ephemeral=True)
        await itx.response.defer(ephemeral=True, thinking=True)
        lim = limit or int(self.cfg.get("backfill_default_limit", 800)); lim = max(50, min(5000, lim))
        ch = itx.channel
        rid = self._mapped_role_for(getattr(ch, "id", 0)) if ch else None
        if not rid or rid not in self.allowed_roles:
            return await itx.followup.send("Channel/thread ini tidak dipetakan di config.", ephemeral=True)

        authors = await self._iter_recent_authors(ch, lim)  # type: ignore
        added = 0
        for uid in authors:
            try:
                m = itx.guild.get_member(int(uid))
                if not m: continue
                if rid not in [r.id for r in m.roles]:
                    await self._grant(m, int(rid)); added += 1
                    await asyncio.sleep(max(0.15, self.cfg.get("prune_sleep_ms_per_action", 300)/1000.0))
            except Exception:
                pass
        await itx.followup.send(f"Backfill selesai. Ditambahkan: {added}", ephemeral=True)
async def setup(bot: commands.Bot):
    await bot.add_cog(AutoRoleAnywhere(bot))