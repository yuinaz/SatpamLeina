import logging
import traceback
from discord.ext import commands
from discord import Message, Forbidden, HTTPException, NotFound

logger = logging.getLogger(__name__)

async def handle_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Argumen yang dibutuhkan tidak lengkap.")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Perintah tidak ditemukan.")
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("❌ Kamu tidak memiliki izin untuk menjalankan perintah ini.")
    else:
        await ctx.send("❌ Terjadi kesalahan yang tidak diketahui.")
        tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        logger.error(f"Error on command {ctx.command}: {tb}")

async def handle_on_error(event_method, *args, **kwargs):
    logger.warning(f"⚠️ Event error in {event_method}")
    if event_method == "on_message":
        message: Message = args[0]
        logger.warning(f"Message content: {message.content}")
    tb = traceback.format_exc()
    logger.error(f"Traceback:\n{tb}")


def setup_error_handler(bot: commands.Bot):
    """Register generic error handlers to the bot."""
    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    # Patched: avoid duplicate usage messages for optional args like testban
        try:
            await handle_error(ctx, error)
        except Exception:
            # fallback logging
            import traceback, logging
            logging.getLogger(__name__).error("[setup_error_handler] failed to handle error:\n" + traceback.format_exc())

    @bot.event
    async def on_error(event_method, *args, **kwargs):
        try:
            await handle_on_error(event_method, *args, **kwargs)
        except Exception:
            import traceback, logging
            logging.getLogger(__name__).error("[setup_error_handler] on_error fallback:\n" + traceback.format_exc())
