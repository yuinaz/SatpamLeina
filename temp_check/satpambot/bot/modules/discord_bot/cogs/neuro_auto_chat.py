from __future__ import annotations

from discord.ext import commands
import os, json, time, asyncio, logging
from pathlib import Path
from typing import Dict, Set

import discord

from discord import app_commands

from satpambot.bot.llm.groq_client import groq_chat
from satpambot.bot.modules.discord_bot.cogs.neuro_memory_core import MemoryStore

log = logging.getLogger(__name__)

SETTINGS_PATH = os.getenv("NEURO_SETTINGS", "data/neuro_settings.json")
COOLDOWN_SEC = int(os.getenv("NEURO_COOLDOWN", "8"))

def _load_settings() -> dict:
    p = Path(SETTINGS_PATH)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"allowed_channels": [], "mode": "mention"}, indent=2))
    try:
        return json.loads(p.read_text())
    except Exception:
        return {"allowed_channels": [], "mode": "mention"}

def _save_settings(cfg: dict):
    p = Path(SETTINGS_PATH); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg, indent=2))

class NeuroAutoChat(commands.Cog):
    """Groq-powered chat in allowed channels; learns via neuro_memory_core listeners."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings = _load_settings()
        self.cooldowns: Dict[int, float] = {}  # channel_id -> last_ts
        self.db: MemoryStore = getattr(bot, "_neuro_db", None) or MemoryStore()
        setattr(bot, "_neuro_db", self.db)

    # ----- Slash to manage channels & mode -----
    @app_commands.command(name="neuro_channel_add", description="Aktifkan auto-chat di channel ini.")
    async def neuro_channel_add(self, itx: discord.Interaction):
        if not itx.channel: 
            await itx.response.send_message("Harus dipanggil di dalam channel.", ephemeral=True); return
        cid = itx.channel.id
        cfg = self.settings
        if cid not in cfg["allowed_channels"]:
            cfg["allowed_channels"].append(cid); _save_settings(cfg); self.settings = cfg
        await itx.response.send_message(f"✅ Diaktifkan di <#{cid}> (mode: {cfg.get('mode','mention')}).", ephemeral=True)

    @app_commands.command(name="neuro_channel_remove", description="Matikan auto-chat di channel ini.")
    async def neuro_channel_remove(self, itx: discord.Interaction):
        if not itx.channel: 
            await itx.response.send_message("Harus dipanggil di dalam channel.", ephemeral=True); return
        cid = itx.channel.id
        cfg = self.settings
        if cid in cfg["allowed_channels"]:
            cfg["allowed_channels"].remove(cid); _save_settings(cfg); self.settings = cfg
        await itx.response.send_message(f"🛑 Dimatikan di <#{cid}>.", ephemeral=True)

    @app_commands.command(name="neuro_channel_list", description="Lihat channel yang aktif.")
    async def neuro_channel_list(self, itx: discord.Interaction):
        cfg = self.settings
        chs = cfg.get("allowed_channels", [])
        mode = cfg.get("mode", "mention")
        if not chs:
            await itx.response.send_message(f"(kosong) — mode: {mode}", ephemeral=True); return
        s = ", ".join(f"<#{c}>" for c in chs)
        await itx.response.send_message(f"Aktif di: {s}\nMode: `{mode}` (mention/auto)", ephemeral=True)

    @app_commands.command(name="neuro_mode", description="Ubah mode pemicu: mention (default) atau auto.")
    @app_commands.describe(mode="mention atau auto")
    async def neuro_mode(self, itx: discord.Interaction, mode: str):
        mode = mode.lower().strip()
        if mode not in {"mention", "auto"}:
            await itx.response.send_message("Gunakan: mention / auto", ephemeral=True); return
        cfg = self.settings; cfg["mode"] = mode; _save_settings(cfg); self.settings = cfg
        await itx.response.send_message(f"Mode di-set ke `{mode}`.", ephemeral=True)

    # ----- Core on_message -----
    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if m.author.bot or not m.guild: return
        cfg = self.settings
        if m.channel.id not in cfg.get("allowed_channels", []): return

        # trigger conditions
        mode = cfg.get("mode", "mention")
        triggered = False
        if mode == "mention":
            triggered = any(u.id == self.bot.user.id for u in getattr(m, "mentions", []))
        else:
            triggered = True  # auto mode: every message

        if not triggered: return

        # cooldown per channel
        now = time.time()
        last = self.cooldowns.get(m.channel.id, 0.0)
        if now - last < COOLDOWN_SEC:
            return
        self.cooldowns[m.channel.id] = now

        # build context from memory
        query = (m.content or "").strip()
        ctx_items = self.db.search(m.guild.id, m.channel.id, query, top_k=3)
        context_block = "\n".join(f"- {r.content}" for r in ctx_items) or "(none)"

        system = "You are a helpful, concise Discord assistant. Use Bahasa Indonesia when users do. If you need more info, ask a short clarifying question. Keep answers <= 6 sentences."
        user = f"[CONTEXT]\n{context_block}\n\n[USER]\n{query}\n"

        try:
            text = await groq_chat([
                {"role":"system","content":system},
                {"role":"user","content":user},
            ], max_tokens=650)
        except Exception as e:
            log.exception("Groq error: %s", e)
            return

        if not text: return
        if len(text) > 1800: text = text[:1800] + "…"

        try:
            await m.channel.send(text, reference=m if mode=="mention" else None)
        except Exception:
            log.exception("Failed to send neuro reply.")
            return

        # (optional) store user's message quickly (the detailed auto-learn handled in memory cog)
        try:
            if query:
                self.db.upsert(m.guild.id, m.channel.id, m.author.id, query, tags="dialogue,user")
        except Exception:
            pass
async def setup(bot: commands.Bot):
    await bot.add_cog(NeuroAutoChat(bot))