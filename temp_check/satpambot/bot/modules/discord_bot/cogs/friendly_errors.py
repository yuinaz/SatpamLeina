from discord.ext import commands
import logging, discord

log = logging.getLogger("friendly_errors")
async def _infer_member(ctx: commands.Context):
    if ctx.message.mentions:
        m = ctx.message.mentions[0]
        if isinstance(m, discord.Member): return m
        try: return await ctx.guild.fetch_member(m.id)
        except Exception: pass
    try:
        if ctx.message.reference and ctx.message.reference.message_id:
            ref = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if isinstance(ref.author, discord.Member): return ref.author
            try: return await ctx.guild.fetch_member(ref.author.id)
            except Exception: pass
    except Exception: pass
    return None
class FriendlyErrors(commands.Cog):
    def __init__(self, bot): self.bot = bot
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        if hasattr(ctx.command, 'on_error'): return
        error = getattr(error, 'original', error)
        from discord.ext import commands as c
        if isinstance(error, c.MissingRequiredArgument) and error.param.name == "member":
            target = await _infer_member(ctx)
            if target is not None:
                try: await ctx.invoke(ctx.command, member=target); return
                except Exception: pass
            prefix = ctx.clean_prefix or "!"; sig = ctx.command.signature or "<member> [opsi...]"
            ex  = f"{prefix}{ctx.command.qualified_name} @user"
            return await ctx.reply(f"❌ Argumen **member** wajib.\n• Penggunaan: `{prefix}{ctx.command.qualified_name} {sig}`\n• Contoh: `{ex}`\nTip: reply pesan user lalu ketik `{prefix}{ctx.command.qualified_name}`.", delete_after=15)
        if isinstance(error, c.MemberNotFound): return await ctx.reply("❌ User tidak ditemukan.", delete_after=10)
        if isinstance(error, c.BadArgument):   return await ctx.reply("❌ Argumen tidak valid.", delete_after=10)
        if isinstance(error, c.MissingPermissions): return await ctx.reply("❌ Kamu tidak punya izin.", delete_after=10)
        if isinstance(error, c.BotMissingPermissions): return await ctx.reply("❌ Bot kurang izin.", delete_after=10)
        log.exception("Command error: %s", error)
        try: await ctx.reply("⚠️ Error tak terduga. Sudah dicatat di log.", delete_after=10)
        except Exception: pass
async def setup(bot): await bot.add_cog(FriendlyErrors(bot))