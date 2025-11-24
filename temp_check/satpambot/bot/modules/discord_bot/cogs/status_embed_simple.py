from __future__ import annotations

from discord.ext import commands

# NOTE:
# Modul ini DISABLED untuk mencegah embed sticky dobel.
# Gunakan jalur resmi di helpers/log_utils + presence_fix untuk update status.
# Jika ingin mengaktifkan kembali, set env: STICKY_SIMPLE_ENABLE=1 (tidak direkomendasikan).
import os
import discord

ENABLED = str(os.getenv("STICKY_SIMPLE_ENABLE","")).lower() in ("1","true","yes","on")

class StatusEmbedSimple(commands.Cog):
    """Placeholder saja; tidak melakukan apa-apa saat disabled."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
async def setup(bot: commands.Bot):
    if not ENABLED:
        # Jangan load apapun supaya tidak bikin embed kedua.
        try:
            bot.logger.info("[status_embed_simple] disabled (use presence_fix/log_utils only)")
        except Exception:
            print("[status_embed_simple] disabled (use presence_fix/log_utils only)")
        return
    await bot.add_cog(StatusEmbedSimple(bot))