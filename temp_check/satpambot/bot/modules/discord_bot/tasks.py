# Minimal safe tasks stub (OCR/blacklist hooks are handled by handlers/*.py)
import discord
from discord.ext import commands

async def process_image_message(message: discord.Message, bot: commands.Bot):
    return

async def check_ocr_violation(image_bytes: bytes, message: discord.Message, image_hash: str) -> bool:
    return False
