from __future__ import annotations
import os, json, logging, urllib.request
from typing import Optional
import discord
from discord.ext import commands
log = logging.getLogger(__name__)
def _env(k, d=None): v=os.getenv(k); return v if v not in (None,"") else d
def _qna_id():
    try: v=int(_env("QNA_CHANNEL_ID","0") or "0"); return v or None
    except: return None
def _is_q(e): return ((getattr(e,"title","") or "").strip().lower()).startswith("question by leina")
class QnaChannelGateOverlay(commands.Cog):
    def __init__(self, bot): self.bot=bot; self.qna=_qna_id(); log.info("[qna-gate] QNA_CHANNEL_ID=%s", self.qna)
    @commands.Cog.listener()
    async def on_message(self, m: "discord.Message"):
        if not getattr(m, "embeds", None) or len(m.embeds)==0: return
        if not _is_q(m.embeds[0]): return
        if self.qna and getattr(getattr(m,"channel",None),"id",None)!=self.qna:
            try: await m.delete(); log.warning("[qna-gate] removed stray question")
            except Exception as e: log.warning("[qna-gate] remove failed: %r", e)
async def setup(bot): await bot.add_cog(QnaChannelGateOverlay(bot))