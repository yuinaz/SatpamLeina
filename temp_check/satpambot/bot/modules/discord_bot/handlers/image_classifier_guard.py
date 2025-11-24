from __future__ import annotations

import logging, discord
from satpambot.bot.modules.discord_bot.utils.actions import delete_message_safe
from satpambot.bot.modules.discord_bot.helpers.image_classifier import classify_image
from satpambot.bot.modules.discord_bot.helpers.permissions import is_exempt_user, is_whitelisted_channel
from ..helpers.log_utils import find_text_channel

logger = logging.getLogger(__name__)

async def handle_image_classifier(message: discord.Message):
    try:
        if not message or getattr(message.author, "bot", False):
            return
        if is_whitelisted_channel(getattr(message,'channel',None)) or is_exempt_user(getattr(message,'author',None)):
            return
        atts = getattr(message, "attachments", []) or []
        if not atts:
            return
        for att in atts:
            try:
                data = await att.read()
                res = classify_image(data)
                if not res or not res.get("enabled"):
                    continue
                verdict = res.get("verdict")
                if verdict == "black":
                    await delete_message_safe(message, actor='image_classifier_guard')
                    ch = await find_text_channel(message.guild, "log-botphising") if message.guild else None
                    if ch:
                        await ch.send(f"🧹 [ImageGuard] Deleted blacklisted image from {message.author.mention} in {message.channel.mention}")
                    return
            except Exception:
                logger.debug("Image classifier on attachment failed", exc_info=True)
    except Exception:
        logger.debug("handle_image_classifier failed", exc_info=True)
