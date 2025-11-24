from discord.ext import commands
import os, traceback, datetime as dt, discord

WIB = dt.timezone(dt.timedelta(hours=7))
def _now_wib(): return dt.datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")

CHANNEL_ENV_KEYS = ("ERROR_LOG_CHANNEL_ID", "LOG_CHANNEL_ERROR", "LOG_CHANNEL_ID")

def _find_error_channel(guild: discord.Guild):
    if guild is None:
        return None
    for k in CHANNEL_ENV_KEYS:
        try:
            raw = os.getenv(k)
            if raw:
                cid = int(raw)
                ch = guild.get_channel(cid) or next((c for c in guild.text_channels if c.id == cid), None)
                if ch and isinstance(ch, discord.TextChannel):
                    return ch
        except Exception:
            pass
    names = ("errorlog-bot","errorlog","log-bot","log-botphising")
    for name in names:
        ch = discord.utils.get(guild.text_channels, name=name)
        if ch:
            return ch
    return None

def _embed_from_error(title: str, exc: BaseException):
    e = discord.Embed(title=title, color=discord.Color.red())
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    e.description = f"```py\n{tb[-1800:]}\n```"
    e.set_footer(text=f"SatpamBot • {_now_wib()}")
    return e

class ErrorLogBridge(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        if hasattr(ctx.command, "on_error"):
            return
        ch = _find_error_channel(ctx.guild) if ctx.guild else None
        if ch:
            try:
                await ch.send(embed=_embed_from_error(f"❌ Unhandled Exception (prefix) • {ctx.command}", error))
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error: Exception):
        guild = interaction.guild if interaction else None
        ch = _find_error_channel(guild) if guild else None
        if ch:
            try:
                name = getattr(getattr(interaction, "command", None), "name", "unknown")
                await ch.send(embed=_embed_from_error(f"❌ Unhandled Exception (slash) • /{name}", error))
            except Exception:
                pass
async def setup(bot: commands.Bot):
    await bot.add_cog(ErrorLogBridge(bot))