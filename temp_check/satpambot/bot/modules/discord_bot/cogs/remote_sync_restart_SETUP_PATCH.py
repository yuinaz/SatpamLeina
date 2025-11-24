
# PATCHED setup: register slash groups to tree (guild-first), override existing /repo if any
from discord.ext import commands
import os, logging, discord

log = logging.getLogger(__name__)
async def setup(bot: commands.Bot):
    from .remote_sync_restart import RemoteSyncRestart  # local import to avoid circular
    cog = RemoteSyncRestart(bot)
    await bot.add_cog(cog)
    try:
        gid = os.getenv("SB_GUILD_ID")
        if gid:
            guild = discord.Object(id=int(gid))
            # Register both groups; override ensures this version wins for /repo
            bot.tree.add_command(cog.group, guild=guild, override=True)
            bot.tree.add_command(cog.group_rt, guild=guild, override=True)
            synced = await bot.tree.sync(guild=guild)
            log.info("[remote_sync_restart] guild-registered + synced to %s (count=%d)", gid, len(synced))
        else:
            bot.tree.add_command(cog.group, override=True)
            bot.tree.add_command(cog.group_rt, override=True)
            synced = await bot.tree.sync()
            log.info("[remote_sync_restart] global registered + synced (count=%d)", len(synced))
    except Exception as e:
        log.warning("[remote_sync_restart] sync warn: %r", e)