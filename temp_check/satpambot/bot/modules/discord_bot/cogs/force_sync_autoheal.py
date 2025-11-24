from __future__ import annotations

from discord.ext import commands
import os, logging, asyncio
import discord

LOG = logging.getLogger("satpambot.bot.modules.discord_bot.cogs.force_sync_autoheal")

def _owner_ids():
    raw = os.getenv("BOT_OWNER_IDS","") or os.getenv("OWNER_IDS","")
    ids=set()
    for p in raw.replace(";",
",").split(","):
        p=p.strip()
        if p.isdigit(): ids.add(int(p))
    one=os.getenv("OWNER_ID","").strip()
    if one.isdigit(): ids.add(int(one))
    return ids

class ForceSyncAutoHeal(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._did = False
        self._task = None

    async def _sync_all(self):
        # Global
        try:
            await self.bot.tree.sync()
            LOG.info("[autoheal-sync] global synced")
        except Exception as e:
            LOG.exception("[autoheal-sync] global failed: %r", e)
        # Per guild (helps when guild-specific cache desync)
        for g in list(self.bot.guilds):
            try:
                await self.bot.tree.sync(guild=g)
                LOG.info("[autoheal-sync] guild synced: %s (%s)", g.name, g.id)
            except Exception as e:
                LOG.warning("[autoheal-sync] guild failed: %s (%s) %r", g.name, g.id, e)

    @commands.Cog.listener()
    async def on_ready(self):
        if self._did: return
        self._did = True
        # initial sync
        await self._sync_all()
        # retry window (Discord sometimes lags provisioning)
        async def retry():
            delays = [int(os.getenv("RESYNC_RETRY_S","45")), 120]
            for d in delays:
                await asyncio.sleep(d)
                await self._sync_all()
        self._task = asyncio.create_task(retry())

    # Fallback: owner/admin text command (requires message_content intent)
    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if not msg or msg.author.bot: return
        if msg.content.strip().lower() not in {"!resync","!!resync","!sync"}: return
        # owner or admin only
        if msg.guild:
            if isinstance(msg.author, discord.Member) and msg.author.guild_permissions.administrator:
                pass
            elif msg.author.id in _owner_ids():
                pass
            else:
                return
        elif msg.author.id not in _owner_ids():
            return
        try:
            await msg.add_reaction("🔄")
        except Exception: pass
        await self._sync_all()
        try:
            await msg.add_reaction("✅")
        except Exception: pass
async def setup(bot: commands.Bot):
    await bot.add_cog(ForceSyncAutoHeal(bot))