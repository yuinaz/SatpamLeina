from __future__ import annotations

from discord.ext import commands

import os
from typing import Optional, Literal

import discord
from discord import app_commands, Interaction

# --- Simple translation backend (deep-translator then googletrans as fallback) ---
def _translate(text: str, target: str) -> str:
    target = (target or "en").lower()
    # First try deep-translator (lightweight, no API key)
    try:
        from deep_translator import GoogleTranslator  # type: ignore
        return GoogleTranslator(source="auto", target=target).translate(text)
    except Exception:
        pass
    # Fallback: googletrans-py
    try:
        from googletrans import Translator  # type: ignore
        gt = Translator()
        res = gt.translate(text, dest=target)
        return res.text
    except Exception:
        # Last resort: just echo
        return text

LANG_ALIASES = {
    "en": "English",
    "id": "Indonesian",
    "ja": "Japanese",
    "zh": "Chinese (Simplified)",
}

# Slash group: /translate to <en|id|ja|zh> <text>
translate = app_commands.Group(name="translate", description="Translate text/messages")

@translate.command(name="to", description="Translate to a specific language")
@app_commands.describe(language="Target language", text="Text to translate")
async def translate_to(interaction: Interaction,
                       language: Literal["en","id","ja","zh"],
                       text: str) -> None:
    await interaction.response.defer(thinking=True, ephemeral=True)
    out = _translate(text, language)
    label = LANG_ALIASES.get(language, language)
    await interaction.followup.send(f"**{label}:** {discord.utils.escape_markdown(out)}", ephemeral=True)

# Message context menu: Translate 🔤 (target controlled by env, default EN)
async def _ctx_translate(interaction: Interaction, message: discord.Message) -> None:
    target = os.getenv("TRANSLATE_DEFAULT_LANG", "en").lower()
    out = _translate(message.content or "", target)
    label = LANG_ALIASES.get(target, target)
    await interaction.response.send_message(f"**{label}:** {discord.utils.escape_markdown(out)}", ephemeral=True)

CTX_TRANSLATE = app_commands.ContextMenu(name="Translate 🔤", callback=_ctx_translate)

class Translator(commands.Cog):
    """Lightweight translator commands & context menu."""
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
async def setup(bot: commands.Bot) -> None:
    # Add cog (even though it has no listeners; keeps parity with other cogs).
    await bot.add_cog(Translator(bot))
    # Register slash group and context menu on load.
    try:
        bot.tree.add_command(translate)
    except Exception:
        # already added by hot-reload
        pass
    try:
        bot.tree.add_command(CTX_TRANSLATE)
    except Exception:
        pass