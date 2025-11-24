# -*- coding: utf-8 -*-
"""helpers/memory_wb.py (full fix)"""
from __future__ import annotations
import os, json, io
from pathlib import Path
from typing import Iterable, Optional
import discord

LOG_CHANNEL_NAME = os.getenv('LOG_CHANNEL_NAME', 'log-botphising')
LOG_CHANNEL_ID_RAW = os.getenv('LOG_CHANNEL_ID', '').strip()
MEMORY_THREAD_NAME = os.getenv('MEMORY_WB_THREAD_NAME', 'memory W*B')
STATE_FILE = Path('data/memory_wb.json')

def _load_state() -> dict:
    try:
        t = STATE_FILE.read_text(encoding='utf-8')
        d = json.loads(t)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}

def _write_state(state: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass

async def _resolve_log_channel(bot: discord.Client) -> Optional[discord.TextChannel]:
    chan_id = int(LOG_CHANNEL_ID_RAW) if LOG_CHANNEL_ID_RAW.isdigit() else None
    for guild in bot.guilds:
        if chan_id:
            ch = guild.get_channel(chan_id) or discord.utils.get(guild.text_channels, id=chan_id)
            if isinstance(ch, discord.TextChannel):
                return ch
        ch = discord.utils.find(lambda c: isinstance(c, discord.TextChannel) and (c.name or '') == LOG_CHANNEL_NAME, guild.text_channels)
        if isinstance(ch, discord.TextChannel):
            return ch
    return None

async def _get_or_create_thread(ch: discord.TextChannel, name: str) -> Optional[discord.Thread]:
    try:
        threads = []
        try:
            threads.extend(ch.threads)
        except Exception:
            pass
        try:
            arch = await ch.archived_threads(limit=50).flatten()  # type: ignore[attr-defined]
            threads.extend(arch or [])
        except Exception:
            pass
        for t in threads:
            if isinstance(t, discord.Thread) and (t.name or '').lower() == name.lower():
                return t
    except Exception:
        pass
    try:
        starter = await ch.send('Thread untuk memory WL/BL.')
        th = await starter.create_thread(name=name, auto_archive_duration=10080)
        return th
    except Exception:
        return None

def _embed_memory(wl: Iterable[str], bl: Iterable[str]) -> discord.Embed:
    wl_list = list(wl); bl_list = list(bl)
    emb = discord.Embed(title='Memory WL/BL', description='Ringkasan daftar whitelist/blacklist', colour=discord.Colour.blurple())
    emb.add_field(name='Whitelist', value=str(len(wl_list)), inline=True)
    emb.add_field(name='Blacklist', value=str(len(bl_list)), inline=True)
    return emb

def _txt_file(name: str, lines: Iterable[str]) -> discord.File:
    payload = '\n'.join(sorted(set(str(x).strip() for x in lines if str(x).strip())))
    buf = io.BytesIO(payload.encode('utf-8')); buf.seek(0)
    return discord.File(buf, filename=name)

async def update_memory_wb(bot: discord.Client, whitelist: Iterable[str], blacklist: Iterable[str]) -> None:
    ch = await _resolve_log_channel(bot)
    if not ch: return
    th = await _get_or_create_thread(ch, MEMORY_THREAD_NAME)
    if not th: return

    state = _load_state()
    embed = _embed_memory(list(whitelist), list(blacklist))

    # Upsert embed pinned
    msg = None
    embed_id = state.get('embed_message_id')
    if embed_id:
        try:
            msg = await th.fetch_message(embed_id)
            await msg.edit(embed=embed)
        except Exception:
            msg = None
    if msg is None:
        try:
            pins = await th.pins()
        except Exception:
            pins = []
        for p in pins:
            ok_author = False
            try: ok_author = (p.author.id == bot.user.id)  # type: ignore[union-attr]
            except Exception: pass
            ok_title = False
            if p.embeds:
                try:
                    ttl = (p.embeds[0].title or '').strip().lower()
                    ok_title = ttl.startswith('memory wl/bl')
                except Exception: pass
            if ok_author and ok_title:
                msg = p
                try: await msg.edit(embed=embed)
                except Exception: pass
                break
    if msg is None:
        try:
            msg = await th.send(embed=embed)
            try: await msg.pin()
            except Exception: pass
        except Exception:
            msg = None
    if msg is not None:
        state['embed_message_id'] = msg.id

    # Replace attachments
    att_id = state.get('attachments_message_id')
    if att_id:
        try:
            old = await th.fetch_message(att_id)
            try: await old.unpin()
            except Exception: pass
            try: await old.delete()
            except Exception: pass
        except Exception:
            pass
    try:
        new_msg = await th.send(content='Mirror daftar saat ini:', files=[_txt_file('whitelist.txt', whitelist), _txt_file('blacklist.txt', blacklist)])
        state['attachments_message_id'] = new_msg.id
    except Exception:
        pass

    # Cleanup duplicates
    try:
        pins = await th.pins()
    except Exception:
        pins = []
    for p in pins:
        if msg and p.id == msg.id: continue
        ok_author = False
        try: ok_author = (p.author.id == bot.user.id)  # type: ignore[union-attr]
        except Exception: pass
        ok_title = False
        if p.embeds:
            try:
                ttl = (p.embeds[0].title or '').strip().lower()
                ok_title = ttl.startswith('memory wl/bl')
            except Exception: pass
        if ok_author and ok_title:
            try: await p.unpin()
            except Exception: pass
            try: await p.delete()
            except Exception: pass

    try:
        async for h in th.history(limit=200, oldest_first=False):
            if msg and h.id == msg.id: continue
            ok_author = False
            try: ok_author = (h.author.id == bot.user.id)  # type: ignore[union-attr]
            except Exception: pass
            ok_title = False
            if h.embeds:
                try:
                    ttl = (h.embeds[0].title or '').strip().lower()
                    ok_title = ttl.startswith('memory wl/bl')
                except Exception: pass
            if ok_author and ok_title:
                try: await h.delete()
                except Exception: pass
    except Exception:
        pass

    _write_state(state)
