from __future__ import annotations

import logging, discord
from satpambot.bot.modules.discord_bot.utils.actions import delete_message_safe

logger = logging.getLogger(__name__)

async def handle_ocr(message: discord.Message):
    try:
        if not message or getattr(message.author, "bot", False):
            return
        # Placeholder without OCR: nothing to do.
        return
    except Exception:
        logger.debug("handle_ocr failed", exc_info=True)
