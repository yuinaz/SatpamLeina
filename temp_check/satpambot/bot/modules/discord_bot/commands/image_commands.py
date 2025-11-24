from discord.ext import commands
from PIL import Image
import io
import discord
from satpambot.bot.modules.discord_bot.helpers.image_utils import compress_image

def register_image_commands(bot: commands.Bot):
    @bot.command(name="checkimage")
    async def checkimage(ctx: commands.Context):
        """Hitung hash gambar untuk diperiksa"""
        if not ctx.message.attachments:
            await ctx.send("❌ Harap lampirkan gambar.")
            return

        for attachment in ctx.message.attachments:
            if not attachment.content_type.startswith("image/"):
                continue
            image_bytes = await attachment.read()
            await ctx.send(f"🔍 Hash: `{hash(image_bytes)}`")  # Optional hash

    @bot.command(name="compress")
    async def compress(ctx: commands.Context):
        """Kompresi gambar dan kirim ulang"""
        if not ctx.message.attachments:
            await ctx.send("❌ Harap lampirkan gambar.")
            return

        for attachment in ctx.message.attachments:
            if not attachment.content_type.startswith("image/"):
                continue
            image_bytes = await attachment.read()
            image = Image.open(io.BytesIO(image_bytes))
            image = compress_image(image)

            buf = io.BytesIO()
            image.save(buf, format="JPEG")
            buf.seek(0)

            await ctx.send(file=discord.File(buf, filename="compressed.jpg"))
