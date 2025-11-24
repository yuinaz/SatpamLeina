from __future__ import annotations

from discord.ext import commands

import os, json, logging, io, re
import discord
from discord import app_commands
from discord.ext import tasks
from satpambot.bot.modules.discord_bot.helpers.runtime_cfg import ConfigManager

log = logging.getLogger(__name__)

def _is_admin(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    env_ids = os.getenv("ADMIN_USER_IDS")
    if env_ids:
        try:
            allow = {int(t) for t in env_ids.replace(" ", "").split(",") if t.isdigit()}
            if member.id in allow: return True
        except Exception:
            pass
    return False

def _extract_json_from_text(text: str):
    if not text: return None
    m = re.search(r"```(?:json\s*)?(.*?)```", text, re.S|re.I)
    if m:
        raw = m.group(1).strip()
        try: return json.loads(raw)
        except Exception: pass
    try: return json.loads(text)
    except Exception: return None

class RuntimeCfgManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cfg = ConfigManager.instance()
        self.watcher.start()

    def cog_unload(self):
        try: self.watcher.cancel()
        except Exception: pass

    @tasks.loop(seconds=45.0)
    async def watcher(self):
        self.cfg.maybe_reload()

    @watcher.before_loop
    async def before_watcher(self):
        await self.bot.wait_until_ready()

    group = app_commands.Group(name="cfg", description="Runtime config SatpamBot")

    @group.command(name="show", description="Lihat konfigurasi runtime")
    async def show(self, interaction: discord.Interaction):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("Nope.", ephemeral=True); return
        data = self.cfg._data
        text = json.dumps(data, ensure_ascii=False, indent=2)[:1900]
        await interaction.response.send_message(f"```json\n{text}\n```", ephemeral=True)

    @group.command(name="set", description="Set key path (dot) ke value skalar")
    @app_commands.describe(path="contoh: status_pin.interval_min", value="nilai (bool/int/float/string)")
    async def set(self, interaction: discord.Interaction, path: str, value: str):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("Nope.", ephemeral=True); return
        v: object = value
        low = value.strip().lower()
        if low in ("true","false","1","0","on","off"):
            v = low in ("true","1","on")
        else:
            try:
                v = float(value) if "." in value else int(value)
            except Exception:
                v = value
        self.cfg.set(path, v)
        await interaction.response.send_message(f"OK set `{path}` -> `{v}`", ephemeral=True)

    @group.command(name="setlist", description="Set key list via CSV atau JSON array")
    @app_commands.describe(path="contoh: reaction_allow.extra_ids", items="CSV atau JSON array")
    async def setlist(self, interaction: discord.Interaction, path: str, items: str):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("Nope.", ephemeral=True); return
        val = None
        try:
            if items.strip().startswith("["):
                val = json.loads(items)
            else:
                toks = [t for t in [x.strip() for x in items.split(",")] if t]
                if all(t.isdigit() for t in toks):
                    val = [int(t) for t in toks]
                else:
                    val = toks
        except Exception as e:
            await interaction.response.send_message(f"Gagal parse: {e}", ephemeral=True); return
        self.cfg.set(path, val)
        await interaction.response.send_message(f"OK set list `{path}` -> `{val}`", ephemeral=True)

    @group.command(name="import", description="Import JSON dari attachment / teks (merge & simpan)")
    async def import_json(self, interaction: discord.Interaction, json_text: str | None = None):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("Nope.", ephemeral=True); return
        data = None
        if json_text:
            data = _extract_json_from_text(json_text)
        if data is None and interaction.attachments:
            try:
                content = await interaction.attachments[0].read()
                data = json.loads(content.decode("utf-8"))
            except Exception:
                pass
        if data is None:
            await interaction.response.send_message("Tidak ada JSON valid. Kirim teks/attachment JSON.", ephemeral=True); return
        cur = self.cfg._data.copy()
        for k, v in data.items():
            cur[k] = v
        self.cfg.set("", cur)
        await interaction.response.send_message("Config di-import & disimpan.", ephemeral=True)

    @group.command(name="export", description="Export config runtime sebagai file JSON")
    async def export_json(self, interaction: discord.Interaction):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("Nope.", ephemeral=True); return
        b = json.dumps(self.cfg._data, ensure_ascii=False, indent=2).encode("utf-8")
        file = discord.File(io.BytesIO(b), filename="runtime_config.json")
        await interaction.response.send_message(file=file, ephemeral=True)

    @group.command(name="bindmsg", description="Bind ke pesan berisi JSON (reply ke pesannya)")
    async def bindmsg(self, interaction: discord.Interaction):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("Nope.", ephemeral=True); return
        ref = interaction.message.reference if interaction.message else None
        if not ref or not ref.resolved:
            await interaction.response.send_message("Reply ke pesan JSON dulu, lalu jalankan /cfg bindmsg.", ephemeral=True); return
        msg: discord.Message = ref.resolved  # type: ignore
        ch: discord.TextChannel = msg.channel  # type: ignore
        self.cfg.set("config_source.channel_id", int(ch.id))
        self.cfg.set("config_source.message_id", int(msg.id))
        await interaction.response.send_message(f"Bound ke pesan {msg.id} di #{ch.name}. Bot akan mengikuti perubahan JSON.", ephemeral=True)
async def setup(bot: commands.Bot):
    cog = RuntimeCfgManager(bot)
    await bot.add_cog(cog)
    try: bot.tree.add_command(RuntimeCfgManager.group)
    except Exception: pass