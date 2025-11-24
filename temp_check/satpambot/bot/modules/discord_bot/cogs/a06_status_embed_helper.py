from __future__ import annotations

import discord, datetime as dt

def status_embed(title: str, description: str, *, color: int=0x2b9dff, fields: dict[str,str]|None=None) -> discord.Embed:
    emb = discord.Embed(title=title, description=description, color=color, timestamp=dt.datetime.now(dt.timezone.utc))
    if fields:
        for k,v in fields.items():
            emb.add_field(name=k, value=v, inline=False)
    emb.set_footer(text="SatpamLeina status • anti-spam")
    return emb