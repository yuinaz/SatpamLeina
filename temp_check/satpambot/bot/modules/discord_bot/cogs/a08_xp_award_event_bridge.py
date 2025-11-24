from discord.ext import commands

import logging

log = logging.getLogger(__name__)

class XPAwardEventBridge(commands.Cog):
    """Listens to 'xp_add', 'xp.award', 'satpam_xp' events and normalizes them."""
    def __init__(self, bot):
        self.bot = bot

    # compatibility: multiple event names
    async def on_xp_add(self, **kwargs):
        await self._handle(**kwargs)

    async def on_satpam_xp(self, **kwargs):
        await self._handle(**kwargs)

    async def on_xp_award(self, **kwargs):
        await self._handle(**kwargs)

    async def _handle(self, **kwargs):
        try:
            # normalize
            message = kwargs.get("message")
            author = kwargs.get("author") or (getattr(message, "author", None) if message else None)
            user_id = kwargs.get("user_id") or (getattr(author, "id", None) if author else None)
            amount = kwargs.get("amount", kwargs.get("delta", kwargs.get("xp", 1)))
            channel = kwargs.get("channel") or (getattr(message, "channel", None) if message else None)
            channel_id = kwargs.get("channel_id") or (getattr(channel, "id", None) if channel else None)
            guild = kwargs.get("guild") or (getattr(message, "guild", None) if message else None)
            guild_id = kwargs.get("guild_id") or (getattr(guild, "id", None) if guild else None)
            message_id = kwargs.get("message_id") or (getattr(message, "id", None) if message else None)
            reason = kwargs.get("reason") or kwargs.get("why") or "auto"

            if user_id is None:
                raise TypeError("XPAwardEventBridge: user_id missing (got kwargs=%r)" % (kwargs,))
            try:
                amount = int(amount)
            except Exception:
                amount = 1

            # Use XPStoreBridge if present, else call V1 service directly
            bridge = self.bot.get_cog("XPStoreBridge")
            if bridge and hasattr(bridge, "award"):
                await bridge.award(user_id=user_id, amount=amount, guild_id=guild_id,
                                   reason=reason, channel_id=channel_id, message_id=message_id)
            else:
                from satpambot.bot.modules.discord_bot.services import xp_store as xp_v1
                xp_v1.add_xp(guild_id, user_id, amount)

            log.info("[xp-bridge] awarded +%s to %s in guild=%s", amount, user_id, guild_id)
        except Exception as e:
            log.exception("[xp-bridge] on_xp_add failed: %r", e)

async def setup(bot):
    await bot.add_cog(XPAwardEventBridge(bot))