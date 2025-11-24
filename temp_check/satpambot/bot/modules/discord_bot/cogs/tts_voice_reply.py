from discord.ext import commands
import asyncio, io, logging

import discord
import edge_tts
from satpambot.bot.utils import profanity as prof

log = logging.getLogger(__name__)

class TTSVoiceReply(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cfg = getattr(bot, "local_cfg", {})
        tts_cfg = self.cfg.get("TTS", {})
        self.enabled = bool(tts_cfg.get("enabled", True))
        self.voice = tts_cfg.get("voice", "en-US-AriaNeural")
        self.rate  = tts_cfg.get("rate", "+0%")
        self.pitch = tts_cfg.get("pitch", "+0Hz")
        self._cd = commands.CooldownMapping.from_cooldown(1, 6.0, commands.BucketType.user)

    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if not self.enabled or m.author.bot or not m.content:
            return
        if not self.bot.user:
            return
        bot_ids = {self.bot.user.id}
        is_trigger = (
            self.bot.user.mentioned_in(m)
            or (
                m.reference
                and getattr(m.reference, "resolved", None)
                and getattr(m.reference.resolved.author, "id", None) in bot_ids
            )
        )
        if not is_trigger:
            return
        bucket = self._cd.get_bucket(m)
        if bucket and bucket.update_rate_limit():
            return
        try:
            text = m.content.strip()
            if len(text) > 400:
                text = text[:380] + "..."
            text = prof.sanitize(self.bot, text)
            mp3 = await self._speak_bytes(text)
            file = discord.File(io.BytesIO(mp3), filename="reply.mp3")
            await m.reply(content="(voice reply)", file=file, mention_author=False)
        except Exception as e:
            log.warning("TTS fail: %r", e)

    async def _speak_bytes(self, text: str) -> bytes:
        communicate = edge_tts.Communicate(text, self.voice, rate=self.rate, pitch=self.pitch)
        out = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                out.write(chunk["data"])
        return out.getvalue()
async def setup(bot: commands.Bot):
    # auto-register Cog classes defined in this module
    for _name, _obj in list(globals().items()):
        try:
            if isinstance(_obj, type) and issubclass(_obj, commands.Cog):
                await bot.add_cog(_obj(bot))
        except Exception:
            continue