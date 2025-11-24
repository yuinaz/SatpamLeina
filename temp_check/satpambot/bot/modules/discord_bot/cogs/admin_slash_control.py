from __future__ import annotations

from discord.ext import commands
import json, logging
from pathlib import Path
import discord
from discord import app_commands

from satpambot.config.local_cfg import cfg, cfg_bool

log = logging.getLogger(__name__)
LOCAL_PATH = Path(__file__).resolve().parents[5] / "local.json"

def _read_local() -> dict:
    try:
        return json.loads(LOCAL_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _write_local(update: dict) -> dict:
    base = _read_local()
    base.update(update or {})
    tmp = LOCAL_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(LOCAL_PATH)
    return base

def _is_owner(user: discord.abc.User) -> bool:
    try:
        return int(user.id) == int(cfg("OWNER_USER_ID") or 0)
    except Exception:
        return False

class AdminSlash(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message("Gunakan di server (bukan DM).", ephemeral=True)
            return False
        if not (_is_owner(interaction.user) or await self.bot.is_owner(interaction.user)):
            await interaction.response.send_message("Khusus owner.", ephemeral=True)
            return False
        return True

    @app_commands.command(name="gate_status", description="Lihat status publik & DM muzzle.")
    async def gate_status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = _read_local()
        public = bool(data.get("PUBLIC_MODE_ENABLE", cfg_bool("PUBLIC_MODE_ENABLE", False)))
        mentions = bool(data.get("CHAT_MENTIONS_ONLY", cfg_bool("CHAT_MENTIONS_ONLY", True)))
        dm_mode = str(data.get("DM_MUZZLE", cfg("DM_MUZZLE", "log"))).lower()
        await interaction.followup.send(
            f"**Public:** {'ON' if public else 'OFF'}\n"
            f"**Mentions-only:** {'ON' if mentions else 'OFF'}\n"
            f"**DM mode:** `{dm_mode}` (log/owner/off)",
            ephemeral=True
        )

    @app_commands.command(name="gate_unlock", description="Buka gate publik (go public).")
    async def gate_unlock(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        _write_local({"PUBLIC_MODE_ENABLE": True})
        await interaction.followup.send("✅ Gate dibuka (PUBLIC_MODE_ENABLE = true).", ephemeral=True)

    @app_commands.command(name="gate_lock", description="Kunci gate publik (learning-only).")
    async def gate_lock(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        _write_local({"PUBLIC_MODE_ENABLE": False})
        await interaction.followup.send("🔒 Gate dikunci (PUBLIC_MODE_ENABLE = false).", ephemeral=True)

    @app_commands.command(name="mode_mentions", description="Set mentions-only ON/OFF.")
    @app_commands.describe(on="true/false")
    async def mode_mentions(self, interaction: discord.Interaction, on: bool):
        await interaction.response.defer(ephemeral=True)
        _write_local({"CHAT_MENTIONS_ONLY": bool(on)})
        await interaction.followup.send(f"✅ Mentions-only = {on}.", ephemeral=True)

    @app_commands.command(name="dm_mode", description="Set DM muzzle mode: log / owner / off.")
    @app_commands.describe(mode="log/owner/off")
    async def dm_mode(self, interaction: discord.Interaction, mode: str):
        mode = (mode or "").lower().strip()
        if mode not in ("log","owner","off"):
            return await interaction.response.send_message("Pilih: log / owner / off.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        _write_local({"DM_MUZZLE": mode})
        await interaction.followup.send(f"✅ DM_MUZZLE = {mode}.", ephemeral=True)
async def setup(bot: commands.Bot):
    await bot.add_cog(AdminSlash(bot))