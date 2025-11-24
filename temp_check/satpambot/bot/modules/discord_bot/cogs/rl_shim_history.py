
import discord
from discord.errors import Forbidden, HTTPException

_ORIG_HISTORY = discord.abc.Messageable.history

async def _history_proxy(self, *args, **kwargs):
    try:
        async for m in _ORIG_HISTORY(self, *args, **kwargs):
            yield m
    except (Forbidden, HTTPException, Exception):
        return

if getattr(discord.abc.Messageable.history, "__name__", "") != "_history_proxy":
    discord.abc.Messageable.history = _history_proxy
