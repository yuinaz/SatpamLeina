
# modules/discord_bot/helpers/threaded_log.py
import datetime
import discord
from .paginator import send_paginated_embed

async def send_threaded_paginated_embed(channel: discord.TextChannel, title: str, lines, per_page: int = 20, thread_name: str = None, auto_archive_minutes: int = 1440):
    """
    Buat thread dari channel lalu kirim embed paginated di dalamnya.
    Fallback: kalau tidak bisa buat thread, kirim di channel utama.
    """
    if not thread_name:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        thread_name = f"{title} {ts}"
    try:
        thread = await channel.create_thread(
            name=thread_name,
            auto_archive_duration=auto_archive_minutes,
            type=discord.ChannelType.public_thread,
        )
        await send_paginated_embed(thread, title, lines, per_page=per_page)
        return thread
    except Exception:
        # Fallback tanpa thread
        await send_paginated_embed(channel, title, lines, per_page=per_page)
        return None
