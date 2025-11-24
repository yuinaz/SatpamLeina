from __future__ import annotations
import os, logging
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

QNA_ENABLE = os.getenv("QNA_ENABLE", "1") == "1"
QNA_CHANNEL_ID = int(os.getenv("QNA_CHANNEL_ID", "0") or 0)
QNA_CHANNEL_NAME = os.getenv("QNA_CHANNEL_NAME", "").strip()
LLM_GEMINI_MODEL = os.getenv("LLM_GEMINI_MODEL", os.getenv("GEMINI_MODEL", ""))
LLM_GROQ_MODEL = os.getenv("LLM_GROQ_MODEL", os.getenv("GROQ_MODEL", ""))
HAS_GEMINI = bool(os.getenv("GEMINI_API_KEY", ""))
HAS_GROQ = bool(os.getenv("GROQ_API_KEY", ""))

class QnADiagOverlay(commands.Cog):
    """Simple diag to verify QnA config at runtime."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="qna_diag")
    @commands.is_owner()
    async def qna_diag(self, ctx: commands.Context):
        ch_ok = False
        ch = None
        if QNA_CHANNEL_ID:
            ch = self.bot.get_channel(QNA_CHANNEL_ID)
            ch_ok = isinstance(ch, discord.TextChannel)
        if not ch_ok and QNA_CHANNEL_NAME:
            for g in self.bot.guilds:
                for c in g.text_channels:
                    if c.name == QNA_CHANNEL_NAME:
                        ch = c
                        ch_ok = True
                        break
                if ch_ok:
                    break
        lines = [
            f"QNA_ENABLE={QNA_ENABLE}",
            f"QNA_CHANNEL_ID={QNA_CHANNEL_ID} (ok={ch_ok})",
            f"QNA_CHANNEL_NAME='{QNA_CHANNEL_NAME}'",
            f"HAS_GEMINI={HAS_GEMINI} model={LLM_GEMINI_MODEL}",
            f"HAS_GROQ={HAS_GROQ} model={LLM_GROQ_MODEL}",
            "Note: ensure only one answer-listener is enabled to avoid double replies.",
        ]
        await ctx.send("```ini\n" + "\n".join(lines) + "\n```")

async def setup(bot: commands.Bot):
    await bot.add_cog(QnADiagOverlay(bot))
