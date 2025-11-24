from discord.ext import commands
import io
import os
import asyncio
import discord

from discord import app_commands
from typing import Tuple

from satpambot.bot.modules.discord_bot.helpers import static_cfg

MIRROR_TITLE = "Mirror daftar saat ini"
MIRROR_MARK  = "[LIST_MIRROR_PIN]"   # marker in message content to find/edit
WL_NAME = "whitelist.txt"
BL_NAME = "blacklist.txt"

# Optional config hint (file locations) — safe defaults
WL_PATH = getattr(static_cfg, "WHITELIST_PATH", WL_NAME)
BL_PATH = getattr(static_cfg, "BLACKLIST_PATH", BL_NAME)

def _read_text_candidates(fname: str) -> str:
    # Try CWD, satpambot/data, and relative to this file.
    paths = [
        fname,
        os.path.join("satpambot", "data", fname),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", fname),
    ]
    for p in paths:
        try:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read().strip()
        except Exception:
            continue
    # Try helper modules if available
    try:
        from satpambot.bot.modules.discord_bot.cogs import whitelist as _wl
        txt = getattr(_wl, "current_whitelist_text", None)
        if callable(txt):
            v = txt()
            if v: return v
    except Exception:
        pass
    try:
        from satpambot.bot.modules.discord_bot.cogs import auto_lists as _al
        txt = getattr(_al, "current_whitelist_text", None)
        if callable(txt):
            v = txt()
            if v: return v
    except Exception:
        pass
    return ""

def _make_files(wl: str, bl: str) -> Tuple[discord.File, discord.File]:
    wl_bytes = wl.encode("utf-8") if wl else b""
    bl_bytes = bl.encode("utf-8") if bl else b""
    return (discord.File(io.BytesIO(wl_bytes), filename=WL_NAME),
            discord.File(io.BytesIO(bl_bytes), filename=BL_NAME))

async def _find_existing_message(ch: discord.TextChannel, bot_user_id: int) -> discord.Message | None:
    # Prefer pinned message with our marker
    try:
        pins = await ch.pins()
        for m in pins:
            if m.author.id == bot_user_id and MIRROR_MARK in (m.content or ""):
                return m
    except Exception:
        pass
    # Fallback: search recent history for our marker
    try:
        async for m in ch.history(limit=50):
            if m.author.id == bot_user_id and MIRROR_MARK in (m.content or ""):
                return m
    except Exception:
        pass
    return None

class SlashListBroadcast(commands.Cog):
    """Replace repeated postings with single pinned/editing message."""
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="lists_mirror", description="Tampilkan mirror whitelist/blacklist (pinned + auto-edit).")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def lists_mirror(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=False)

        # Load texts
        wl_txt = _read_text_candidates(WL_PATH)
        bl_txt = _read_text_candidates(BL_PATH)

        embed = discord.Embed(title=MIRROR_TITLE, colour=0x3498DB)
        if wl_txt:
            shown = "\n".join(wl_txt.splitlines()[:15])
            more = max(0, len(wl_txt.splitlines()) - 15)
            embed.add_field(
                name="Whitelist",
                value=f"```\n{shown}\n```" + (f"\n…(+{more} baris)" if more else ""),
                inline=False,
            )
        else:
            embed.add_field(name="Whitelist", value="*(kosong)*", inline=False)

        if bl_txt:
            shown = "\n".join(bl_txt.splitlines()[:15])
            more = max(0, len(bl_txt.splitlines()) - 15)
            embed.add_field(
                name="Blacklist",
                value=f"```\n{shown}\n```" + (f"\n…(+{more} baris)" if more else ""),
                inline=False,
            )
        else:
            embed.add_field(name="Blacklist", value="*(kosong)*", inline=False)

        files = _make_files(wl_txt, bl_txt)
        content = MIRROR_MARK  # marker only; keep content minimal

        ch = interaction.channel
        msg = await _find_existing_message(ch, self.bot.user.id)

        if msg is None:
            # Create & pin once
            sent = await ch.send(content=content, embed=embed, files=list(files))
            try:
                await sent.pin()
            except Exception:
                pass
            await interaction.followup.send("Mirror dibuat & dipin.", ephemeral=True)
        else:
            # Edit existing message; replace attachments
            try:
                # Recreate files (discord.File is single-use)
                files = _make_files(wl_txt, bl_txt)
                await msg.edit(content=content, embed=embed, attachments=list(files))
                await interaction.followup.send("Mirror diperbarui (edit pin).", ephemeral=True)
            except Exception:
                # fallback: send new then pin, delete old
                new_files = _make_files(wl_txt, bl_txt)
                new_msg = await ch.send(content=content, embed=embed, files=list(new_files))
                try:
                    await new_msg.pin()
                except Exception:
                    pass
                try:
                    await msg.delete()
                except Exception:
                    pass
                await interaction.followup.send("Mirror baru dikirim (pin) & yang lama dihapus.", ephemeral=True)
async def setup(bot: commands.Bot):
    await bot.add_cog(SlashListBroadcast(bot))