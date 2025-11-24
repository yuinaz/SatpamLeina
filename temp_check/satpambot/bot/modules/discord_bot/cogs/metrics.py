from discord.ext import commands
import discord

from satpambot.bot.modules.discord_bot.helpers.metrics_agg import inc

# Realtime dashboard + DB helpers (safe fallbacks if not present)
try:
    from satpambot.bot.modules.discord_bot.helpers.ws import emit
except Exception:  # pragma: no cover
    def emit(*args, **kwargs):
        pass

try:
    from satpambot.bot.modules.discord_bot.helpers.flaskdb import insert_ban, mark_unban, compute_stats
except Exception:  # pragma: no cover
    def insert_ban(*args, **kwargs):
        pass
    def mark_unban(*args, **kwargs):
        pass
    def compute_stats(guild_id=None):
        return {"core_total": 0, "barLeft": {"labels": [], "values": []}, "topGuilds": [], "bans": []}

class MetricsCog(commands.Cog):
    """Cog metrik. Tambahan: push realtime ke dashboard saat ban/unban."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        # Increment counter legacy
        try:
            inc("moderation.ban")
        except Exception:
            pass
        # Tulis ke DB + emit ke dashboard
        try:
            insert_ban(user.id, getattr(user, "name", str(user.id)), guild.id, "bot-event")
            data = compute_stats(guild.id)
            data["guild_id"] = int(guild.id)
            emit("dashboard:push", data, room=f"guild:{int(guild.id)}")
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        try:
            inc("moderation.unban")
        except Exception:
            pass
        try:
            mark_unban(user.id, guild.id)
            data = compute_stats(guild.id)
            data["guild_id"] = int(guild.id)
            emit("dashboard:push", data, room=f"guild:{int(guild.id)}")
        except Exception:
            pass
async def setup(bot: commands.Bot):
    # Hindari double-register kalau sudah ada
    if bot.get_cog("MetricsCog") is not None:
        return
    await bot.add_cog(MetricsCog(bot))