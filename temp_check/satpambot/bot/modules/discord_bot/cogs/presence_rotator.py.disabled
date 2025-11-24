
from __future__ import annotations
import asyncio, json
from pathlib import Path
import discord
from discord.ext import commands
from typing import Dict

DEFAULT_CFG = {
    "interval_days": 1, "status": "online",
    "activities": [
        {"type": "playing", "name": "🛡️ SatpamLeina /help"},
        {"type": "watching", "name": "laporan phish masuk"},
        {"type": "listening", "name": "laporan @Staff LeinDiscord"},
        {"type": "competing", "name": "perburuan link palsu"}
    ]
}

def _status_from_str(s: str) -> discord.Status:
    return {
        "online": discord.Status.online,
        "idle": discord.Status.idle,
        "dnd": discord.Status.do_not_disturb,
        "invisible": discord.Status.invisible,
    }.get((s or "online").lower(), discord.Status.online)

def _activity(d: Dict) -> discord.BaseActivity | None:
    t = (d.get("type") or "playing").lower(); name = d.get("name") or ""
    if not name: return None
    if t == "playing": return discord.Game(name=name)
    atype = {
        "watching": discord.ActivityType.watching,
        "listening": discord.ActivityType.listening,
        "competing": discord.ActivityType.competing,
        "streaming": discord.ActivityType.streaming
    }.get(t, discord.ActivityType.playing)
    return discord.Activity(type=atype, name=name)

class PresenceRotator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cfg_path = Path("config") / "presence_rotator.json"
        self.state_path = Path("data") / "presence_rotator_state.json"
        self.cfg = DEFAULT_CFG.copy(); self.idx = 0; self._started = False

    def _load_cfg(self):
        try:
            self.cfg_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.cfg_path.exists():
                self.cfg_path.write_text(json.dumps(DEFAULT_CFG, ensure_ascii=False, indent=2), encoding="utf-8")
            self.cfg = json.loads(self.cfg_path.read_text(encoding="utf-8"))
        except Exception:
            self.cfg = DEFAULT_CFG.copy()
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            if self.state_path.exists():
                self.idx = int(json.loads(self.state_path.read_text(encoding="utf-8")).get("idx", 0))
        except Exception:
            self.idx = 0
        acts = self.cfg.get("activities") or []
        if not acts: self.cfg = DEFAULT_CFG.copy()
        self.idx %= len(self.cfg["activities"])

    def _save_state(self):
        try: self.state_path.write_text(json.dumps({"idx": self.idx}), encoding="utf-8")
        except Exception: pass

    async def _apply(self):
        acts = self.cfg.get("activities") or []
        if not acts: return
        self.idx %= len(acts)
        act = _activity(acts[self.idx]); status = _status_from_str(self.cfg.get("status"))
        try: await self.bot.change_presence(activity=act, status=status)
        except Exception: pass

    def _interval(self) -> int:
        try: d = int(self.cfg.get("interval_days", 1))
        except Exception: d = 1
        return max(1, d)*86400

    async def _runner(self):
        await self.bot.wait_until_ready(); self._load_cfg(); await self._apply()
        while not self.bot.is_closed():
            await asyncio.sleep(self._interval())
            self.idx = (self.idx + 1) % len(self.cfg.get("activities") or [None])
            await self._apply()
            self._save_state()

    @commands.Cog.listener()
    async def on_ready(self):
        if self._started: return
        self._started = True; asyncio.create_task(self._runner())

    from discord import app_commands
    grp = app_commands.Group(name="presence", description="Presence rotator")

    @grp.command(name="reload")
    async def reload_cmd(self, itx: discord.Interaction):
        if not itx.user.guild_permissions.manage_guild:
            return await itx.response.send_message("Butuh izin Manage Server.", ephemeral=True)
        self._load_cfg(); await self._apply(); await itx.response.send_message("Presence di-reload ✅", ephemeral=True)

    @grp.command(name="rotate_now")
    async def rotate_now(self, itx: discord.Interaction):
        if not itx.user.guild_permissions.manage_guild:
            return await itx.response.send_message("Butuh izin Manage Server.", ephemeral=True)
        self.idx += 1; await self._apply(); await itx.response.send_message("Presence diganti ✅", ephemeral=True)

async def setup(bot: commands.Bot):
    cog = PresenceRotator(bot); await bot.add_cog(cog)
    try: bot.tree.add_command(cog.grp)
    except Exception: pass
