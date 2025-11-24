# -*- coding: utf-8 -*-
"""
progress_embed_solo (fixed minimal)
Expose: `async def update_embed(bot, channel, embed, pin=False, key="status:progress")`
- Aman di‑await walau EmbedScribe.upsert bukan coroutine (dibungkus maybe‑await).
- `channel` boleh object channel atau integer channel_id.
- `embed` boleh discord.Embed atau dict(title, description, fields=[{name,value,inline}]).
"""
import logging, inspect, asyncio

log = logging.getLogger(__name__)
EMBED_KEY = "status:progress"

async def _maybe_await(v):
    if inspect.isawaitable(v):
        return await v
    return v

def _to_embed(obj):
    try:
        import discord
    except Exception:
        return obj  # di offline sanity, stub discord tidak butuh konversi
    if getattr(obj, "__class__", None).__name__ == "Embed":
        return obj
    if isinstance(obj, dict):
        e = discord.Embed(title=obj.get("title"), description=obj.get("description"))
        for f in obj.get("fields", []):
            name = f.get("name")
            value = f.get("value")
            inline = bool(f.get("inline", False))
            if name and value is not None:
                try:
                    e.add_field(name=name, value=value, inline=inline)
                except Exception:
                    pass
        return e
    return obj

async def update_embed(bot, channel, embed, pin=False, key=EMBED_KEY):
    from satpambot.bot.utils.embed_scribe import EmbedScribe
    ch = channel
    # jika yang dikirim angka, resolve channel dari bot
    if isinstance(channel, int):
        ch = getattr(bot, "get_channel", lambda _id: None)(channel)
        if ch is None and hasattr(bot, "fetch_channel"):
            try:
                ch = await bot.fetch_channel(channel)
            except Exception:
                ch = None
    e = _to_embed(embed)
    scribe = EmbedScribe(bot)
    try:
        return await _maybe_await(scribe.upsert(ch, key, e, pin=pin))
    except Exception as e:
        log.warning("[progress_embed_solo] update error: %r", e)
        return None
async def setup(bot):
    return None
