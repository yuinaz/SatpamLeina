
# satpambot/bot/modules/discord_bot/cogs/prefix_mod_only.py
from discord.ext import commands
import logging

from satpambot.bot.modules.discord_bot.helpers.prefix_guard import get_prefix

log = logging.getLogger(__name__)

class PrefixModOnly(commands.Cog):
    """Batasi prefix '!' hanya untuk MOD. Non-mod silent (tanpa error di channel)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Set callable prefix yang aman untuk DM/Thread
        self.bot.command_prefix = get_prefix  # type: ignore

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        # Jangan spam error ke channel—log saja (hindari crash akibat unhandled error)
        try:
            log.warning("Command error by %s in #%s: %s", getattr(ctx.author, "id", "?"), getattr(ctx.channel, "id", "?"), repr(error))
        except Exception:
            pass
async def setup(bot: commands.Bot):
    await bot.add_cog(PrefixModOnly(bot))