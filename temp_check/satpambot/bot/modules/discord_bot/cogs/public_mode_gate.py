from __future__ import annotations

from discord.ext import commands

import os
import asyncio
from typing import List
import discord
from discord.ext import tasks

from . import __name__ as pkg_name  # just to please import tools
from ..helpers import progress_gate as gate

def _owner_ids() -> List[int]:
    raw = os.getenv("DISCORD_OWNER_IDS") or os.getenv("OWNER_IDS") or ""
    out: List[int] = []
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except Exception:
            pass
    return out

def _is_owner(user: discord.abc.User) -> bool:
    ids = _owner_ids()
    return user.id in ids if ids else user.guild_permissions.administrator if isinstance(user, discord.Member) else True

class PublicModeGate(commands.Cog):
    """DM-only command to toggle public chat replies when learning progress ready (>= threshold)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Heartbeat untuk auto-DM owner saat 100% tercapai
        self.nudge_owner_loop.start()

    def cog_unload(self):
        self.nudge_owner_loop.cancel()

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

        # Only DM commands here, ignore guild
        if message.guild is not None:
            return
        if message.author.bot:
            return
        content = (message.content or "").strip().lower()
        if not content.startswith(("!public", "/public", "public ")):
            return

        if not _is_owner(message.author):
            await message.channel.send("❌ Hanya owner yang bisa mengubah mode publik.")
            return

        args = content.replace("/public", "!public").split()
        cmd = args[0] if args else "!public"
        param = args[1] if len(args) > 1 else "status"

        prog = gate.get_progress()
        need = gate.required_ratio()

        if param in ("on", "enable"):
            if prog.ratio >= need and prog.accuracy >= need:
                gate.set_public_open(True)
                os.environ["SILENT_PUBLIC"] = "0"  # bantu modul lain yang cek ENV
                await message.channel.send(f"✅ Public replies ENABLED (progress {prog.ratio*100:.1f}%, accuracy {prog.accuracy*100:.1f}%).")
            else:
                await message.channel.send(
                    f"⏳ Belum siap. Progress {prog.ratio*100:.1f}% / akurasi {prog.accuracy*100:.1f}% (butuh {need*100:.0f}%). Gunakan `!public status`."
                )
        elif param in ("off", "disable"):
            gate.set_public_open(False)
            os.environ["SILENT_PUBLIC"] = "1"
            await message.channel.send("🛑 Public replies DISABLED. Bot tetap observasi (self-learning) & DM aktif.")
        else:
            state = "ENABLED" if gate.is_public_allowed() else "DISABLED"
            await message.channel.send(
                f"ℹ️ Status: {state} — progress {prog.ratio*100:.1f}% | akurasi {prog.accuracy*100:.1f}% | ambang {need*100:.0f}%.\n"
                f"Perintah: `!public on` / `!public off` / `!public status` (DM only)."
            )

    @tasks.loop(minutes=30.0)
    async def nudge_owner_loop(self):
        """Setiap 30 menit, kalau 100% tercapai tapi publik belum dibuka, DM owner untuk minta izin."""
        if gate.get_public_open():
            return
        prog = gate.get_progress()
        need = gate.required_ratio()
        ready = (prog.ratio >= need and prog.accuracy >= need)
        if not ready or gate.get_open_request_sent():
            return

        owners = _owner_ids()
        for oid in owners:
            user = self.bot.get_user(oid)
            if user is None:
                try:
                    user = await self.bot.fetch_user(oid)  # type: ignore
                except Exception:
                    continue
            try:
                await user.send(
                    f"🤖 SatpamBot siap dibuka di publik.\n"
                    f"- Progress: {prog.ratio*100:.1f}%\n- Akurasi: {prog.accuracy*100:.1f}%\n- Sampel: {prog.samples}\n\n"
                    f"Balas dengan `!public on` untuk mengaktifkan reply publik (mention-only)."
                )
                gate.set_open_request_sent(True)
            except Exception:
                pass
async def setup(bot: commands.Bot):
    await bot.add_cog(PublicModeGate(bot))