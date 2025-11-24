from __future__ import annotations

from typing import Union
import discord
from .message_keeper import get_keeper

async def upsert_status(bot: discord.Client, channel: Union[int, str, discord.abc.Messageable], key: str, text: str):
    keeper = get_keeper(bot)
    await keeper.update(channel, key, content=text)
