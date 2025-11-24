from __future__ import annotations

from discord.ext import commands
import json, logging
from pathlib import Path
import discord
from discord import app_commands

from satpambot.config.local_cfg import cfg, cfg_bool, cfg_int

log = logging.getLogger(__name__)
LOCAL_PATH = Path(__file__).resolve().parents[5] / "local.json"
ITEMS = ["redirect_owner","qna","progress","xp","ratelimit","error_redirect"]

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

class InterviewGate(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message("Gunakan di server (bukan DM).", ephemeral=True)
            return False
        if not (_is_owner(interaction.user) or await self.bot.is_owner(interaction.user)):
            await interaction.response.send_message("Khusus owner.", ephemeral=True)
            return False
        ch_id = int(cfg_int("INTERVIEW_CHANNEL_ID", 0) or 0)
        if ch_id and int(interaction.channel_id or 0) != ch_id:
            await interaction.response.send_message("Gunakan di channel interview yang ditentukan.", ephemeral=True)
            return False
        return True

    @app_commands.command(name="interview_status", description="Lihat checklist dan status interview publik.")
    async def interview_status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = _read_local()
        status = data.get("INTERVIEW_ITEMS", {})
        lines = []
        for k in ITEMS:
            ok = "✅" if status.get(k) else "❌"
            lines.append(f"- {k}: {ok}")
        approved = bool(data.get("INTERVIEW_APPROVED", False))
        public = bool(data.get("PUBLIC_MODE_ENABLE", False))
        await interaction.followup.send(
            "**Interview Checklist**\n" + "\n".join(lines) + f"\n\n**APPROVED:** {approved}\n**PUBLIC_MODE_ENABLE:** {public}",
            ephemeral=True
        )

    @app_commands.command(name="interview_pass", description="Tandai satu item checklist sebagai PASSED.")
    @app_commands.describe(item=f"One of: {', '.join(ITEMS)}")
    async def interview_pass(self, interaction: discord.Interaction, item: str):
        await interaction.response.defer(ephemeral=True)
        item = (item or "").strip().lower()
        if item not in ITEMS:
            return await interaction.followup.send(f"Pilih salah satu: {', '.join(ITEMS)}", ephemeral=True)
        data = _read_local()
        st = dict(data.get("INTERVIEW_ITEMS") or {})
        st[item] = True
        _write_local({"INTERVIEW_ITEMS": st})
        await interaction.followup.send(f"✅ `{item}` ditandai PASSED.", ephemeral=True)

    @app_commands.command(name="interview_fail", description="Tandai satu item checklist sebagai FAILED.")
    @app_commands.describe(item=f"One of: {', '.join(ITEMS)}")
    async def interview_fail(self, interaction: discord.Interaction, item: str):
        await interaction.response.defer(ephemeral=True)
        item = (item or "").strip().lower()
        if item not in ITEMS:
            return await interaction.followup.send(f"Pilih salah satu: {', '.join(ITEMS)}", ephemeral=True)
        data = _read_local()
        st = dict(data.get("INTERVIEW_ITEMS") or {})
        st[item] = False
        _write_local({"INTERVIEW_ITEMS": st})
        await interaction.followup.send(f"❌ `{item}` ditandai FAILED.", ephemeral=True)

    @app_commands.command(name="interview_reset", description="Reset semua checklist interview.")
    async def interview_reset(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        _write_local({"INTERVIEW_ITEMS": {}, "INTERVIEW_APPROVED": False})
        await interaction.followup.send("🔄 Checklist direset.", ephemeral=True)

    @app_commands.command(name="interview_approve", description="Approve dan buka public mode (jika semua item PASSED).")
    async def interview_approve(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = _read_local()
        st = dict(data.get("INTERVIEW_ITEMS") or {})
        missing = [k for k in ITEMS if not st.get(k)]
        if missing:
            return await interaction.followup.send("Belum bisa approve. Item belum PASSED: " + ", ".join(missing), ephemeral=True)
        data = _write_local({"INTERVIEW_APPROVED": True, "PUBLIC_MODE_ENABLE": True})
        await interaction.followup.send("✅ Interview APPROVED. Public mode diizinkan (PUBLIC_MODE_ENABLE=true).", ephemeral=True)
async def setup(bot: commands.Bot):
    await bot.add_cog(InterviewGate(bot))