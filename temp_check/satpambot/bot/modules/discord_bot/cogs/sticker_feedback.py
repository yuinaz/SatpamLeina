from discord.ext import commands
import logging

import discord

from ..helpers.sticker_learner import StickerLearner
try:
    from ...config import envcfg
except Exception:
    envcfg = None

log = logging.getLogger("satpambot.sticker_feedback")

POS = set(["👍","❤️","😂","🙂","😄","🎉","😆","🥰","🔥","😍","👏"])
NEG = set(["👎","😡","😠","💢","😞","😢","🙄","😒"])

def _is_pos(name_or_str: str) -> bool:
    s = str(name_or_str)
    return s in POS or s.lower() in ("thumbsup","heart","joy","tada","clap","fire")

def _is_neg(name_or_str: str) -> bool:
    s = str(name_or_str)
    return s in NEG or s.lower() in ("thumbsdown","angry","rage","cry","disappointed","unamused")

class StickerFeedback(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.learner = StickerLearner()

    async def _handle(self, payload: discord.RawReactionActionEvent, add: bool):
        msg_id = int(payload.message_id)
        emoji = payload.emoji
        emo = self.learner.get_sent_emotion(msg_id)
        if emo is None:
            return
        is_pos = _is_pos(getattr(emoji, "name", None) or str(emoji))
        is_neg = _is_neg(getattr(emoji, "name", None) or str(emoji))
        if not (is_pos or is_neg):
            return
        delta = 1 if add else -1
        self.learner.record_reaction(msg_id, is_positive=is_pos, delta=delta)
        pos_th = envcfg.sticker_pos_threshold() if envcfg else 2
        neg_th = envcfg.sticker_neg_threshold() if envcfg else 1
        credited = self.learner.maybe_credit_success_from_feedback(msg_id, pos_th, neg_th)
        if credited:
            log.info("[sticker_feedback] credited success for message %s (emoji=%s)", msg_id, emoji)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self._handle(payload, add=True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self._handle(payload, add=False)
async def setup(bot: commands.Bot):
    await bot.add_cog(StickerFeedback(bot))