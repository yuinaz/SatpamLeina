
from discord.ext import commands
import discord, os, platform, socket, asyncio

from ..helpers.env import LOG_CHANNEL_ID
from ..helpers.log_utils import upsert_status_embed_in_channel

class Health(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._hb_tasks: dict[int, asyncio.Task] = {}

    @commands.command(name="sbhealth")
    async def sbhealth(self, ctx: commands.Context):
        intents = self.bot.intents
        perms = ctx.guild.me.guild_permissions if ctx.guild and ctx.guild.me else None
        embed = discord.Embed(title="SatpamBot Health", color=discord.Color.blue())
        embed.add_field(
            name="Intents",
            value=f"message_content={getattr(intents,'message_content',None)}, "
                  f"members={getattr(intents,'members',None)}, "
                  f"guilds={getattr(intents,'guilds',None)}",
            inline=False,
        )
        ptxt = ", ".join([k for k in ["manage_messages","ban_members","moderate_members","administrator"]
                          if getattr(perms,k,False)]) if perms else "-"
        embed.add_field(name="Perms", value=ptxt, inline=False)
        embed.add_field(name="Prefix", value=getattr(self.bot, 'command_prefix', '!'), inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="sbwho")
    async def sbwho(self, ctx: commands.Context):
        exts = sorted(self.bot.extensions.keys())
        cogs = sorted(self.bot.cogs.keys())
        embed = discord.Embed(title="SatpamBot Loaded", color=discord.Color.green())
        embed.add_field(name="Extensions", value=(", ".join(exts) or "-"), inline=False)
        embed.add_field(name="Cogs", value=(", ".join(cogs) or "-"), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="sbpid")
    async def sbpid(self, ctx: commands.Context):
        host = socket.gethostname()
        await ctx.send(f"Host={host} | PID={os.getpid()} | Python={platform.python_version()}")

    # 🔎 NEW: cek channel target yang dipakai
    @commands.command(name="sblogtarget", aliases=["sblog"])
    @commands.has_permissions(manage_guild=True)
    async def sblogtarget(self, ctx: commands.Context):
        ch = ctx.guild.get_channel(LOG_CHANNEL_ID) if ctx.guild else None
        if isinstance(ch, discord.TextChannel):
            await ctx.send(f"LOG_CHANNEL_ID → {ch.mention} (name='{ch.name}', id={ch.id})")
        else:
            await ctx.send(f"Tidak dapat melihat channel dengan ID {LOG_CHANNEL_ID}. Cek izin & ENV.", delete_after=10)

    @commands.command(name="sbstatus")
    @commands.has_permissions(manage_guild=True)
    async def sbstatus(self, ctx: commands.Context):
        if not ctx.guild:
            await ctx.send("Jalankan di dalam server."); return
        log_ch = ctx.guild.get_channel(LOG_CHANNEL_ID) if LOG_CHANNEL_ID else None
        if not isinstance(log_ch, discord.TextChannel):
            await ctx.message.add_reaction("❌")
            await ctx.send(f"Tidak menemukan channel log <#{LOG_CHANNEL_ID}>.", delete_after=10)
            return
        ok = await upsert_status_embed_in_channel(self.bot, log_ch)
        await ctx.message.add_reaction("✅" if ok else "❌")
        if ctx.channel.id != log_ch.id:
            await ctx.send(f"Status diperbarui di {log_ch.mention}.", delete_after=6)

    @commands.command(name="sbheartbeat")
    @commands.has_permissions(manage_guild=True)
    async def sbheartbeat(self, ctx: commands.Context, toggle: str = "on"):
        if not ctx.guild:
            await ctx.send("Jalankan di dalam server."); return
        log_ch = ctx.guild.get_channel(LOG_CHANNEL_ID) if LOG_CHANNEL_ID else None
        if not isinstance(log_ch, discord.TextChannel):
            await ctx.send(f"Tidak menemukan channel log <#{LOG_CHANNEL_ID}>.", delete_after=10)
            return

        key = ctx.guild.id
        if toggle.lower() == "off":
            t = self._hb_tasks.pop(key, None)
            if t:
                try: t.cancel()
                except Exception: pass
            await ctx.message.add_reaction("✅")
            if ctx.channel.id != log_ch.id:
                await ctx.send(f"Heartbeat dimatikan untuk {log_ch.mention}.", delete_after=6)
            return

        async def loop():
            while True:
                try:
                    await upsert_status_embed_in_channel(self.bot, log_ch)
                    await asyncio.sleep(600)  # 10 menit
                except asyncio.CancelledError:
                    break
                except Exception:
                    await asyncio.sleep(600)

        old = self._hb_tasks.get(key)
        if old:
            try: old.cancel()
            except Exception: pass
        self._hb_tasks[key] = asyncio.create_task(loop())

        await ctx.message.add_reaction("✅")
        if ctx.channel.id != log_ch.id:
            await ctx.send(f"Heartbeat diaktifkan di {log_ch.mention}. (Loop dikunci ke channel log)", delete_after=8)
async def setup(bot: commands.Bot):
    await bot.add_cog(Health(bot))