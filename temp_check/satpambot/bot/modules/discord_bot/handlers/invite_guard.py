from __future__ import annotations

import re, logging, discord
from satpambot.bot.modules.discord_bot.utils.actions import delete_message_safe

logger = logging.getLogger(__name__)
INVITE_RE = re.compile(r"(?:https?://)?(?:discord(?:app)?\.com/invite/|discord\.gg/|dis\.gd/)([A-Za-z0-9-]+)", re.I)

async def check_nsfw_invites(message: discord.Message, bot):
    try:
        if not message or getattr(message.author, "bot", False):
            return
        text = getattr(message, "content", "") or ""
        if INVITE_RE.search(text):
            await delete_message_safe(message, actor="InviteGuard")
    except Exception:
        logger.debug("check_nsfw_invites failed", exc_info=True)
