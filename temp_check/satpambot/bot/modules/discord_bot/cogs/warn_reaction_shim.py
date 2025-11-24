from __future__ import annotations

from discord.ext import commands

# Shim: hide warn (⚠️) reaction without disabling any learning features.
# This cog monkey-patches the underlying call that adds the warning reaction.
# If the project uses a helper like add_warn_reaction(msg), we intercept it.
import os

FILTER = os.getenv("REACT_WARN_FILTER", "⚠")
ENABLE = os.getenv("REACT_WARN_ENABLE", "false").lower() not in ("0","false","no","off")

def _should_filter(emoji: str) -> bool:
    return ENABLE and (emoji == FILTER or emoji.startswith(FILTER))

class WarnReactionShim(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Try to patch common helpers dynamically
        # If helper not found, we patch Message.add_reaction via a wrapper
        import discord

        orig_add_reaction = discord.Message.add_reaction

        async def add_reaction_wrapper(self, emoji):
            try:
                if _should_filter(str(emoji)):
                    # Swallow silently
                    return
            except Exception:
                pass
            return await orig_add_reaction(self, emoji)

        # Monkey-patch once
        discord.Message.add_reaction = add_reaction_wrapper

    @commands.Cog.listener()
    async def on_ready(self):
        # just to log once
        print("[warn_reaction_shim] aktif; filter:", FILTER, "enabled:", ENABLE)
async def setup(bot: commands.Bot):
    await bot.add_cog(WarnReactionShim(bot))