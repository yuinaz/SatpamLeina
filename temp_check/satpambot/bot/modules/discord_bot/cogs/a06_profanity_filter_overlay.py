from discord.ext import commands
import logging, asyncio

import discord
from satpambot.bot.utils import profanity as prof

log = logging.getLogger(__name__)
async def setup(bot: commands.Bot):
    await bot.add_cog(ProfanityFilterOverlay(bot))

class ProfanityFilterOverlay(commands.Cog):
    """Overlay: patch Messageable.send to sanitize outgoing messages and add sticker once if filtered."""
    def __init__(self, bot):
        self.bot = bot
        self._patch_send()

    def _patch_send(self):
        if getattr(discord.abc.Messageable, "_pf_patched", False):
            return
        orig_send = discord.abc.Messageable.send

        async def send_patched(self_msgable, content=None, **kwargs):
            text = content if isinstance(content, str) else (str(content) if content is not None else None)
            filtered = text
            triggered = False
            if text is not None:
                sanitized = prof.sanitize(self.bot, text)
                triggered = (sanitized != text)
                filtered = sanitized
            send_kwargs = dict(kwargs)
            if filtered is not None:
                content = filtered
            msg = await orig_send(self_msgable, content=content, **send_kwargs)
            try:
                if triggered:
                    ch = getattr(msg, "channel", None)
                    guild = getattr(ch, "guild", None)
                    st = prof.pick_filter_sticker(guild, self.bot)
                    if st:
                        try:
                            await asyncio.sleep(0.1)
                            await ch.send(stickers=[st])
                        except Exception as e:
                            log.debug("[profanity] sticker send failed: %r", e)
            except Exception:
                pass
            return msg

        discord.abc.Messageable.send = send_patched
        discord.abc.Messageable._pf_patched = True
        log.info("[profanity_filter] Messageable.send patched")