
# -*- coding: utf-8 -*-
"""Sticky Keeper helper
Persist and recover sticky message IDs per (channel, marker).
"""
import os, json, asyncio, contextlib, hashlib, time
from typing import Optional
from discord import NotFound
from discord.abc import Messageable
from discord import TextChannel, Thread

_INDEX_PATH = os.getenv("STICKY_KEEPER_PATH", os.path.join("data", "runtime", "sticky_keeper.json"))
os.makedirs(os.path.dirname(_INDEX_PATH), exist_ok=True)

_lock = asyncio.Lock()
_index = {}  # key -> {'id': int, 'hash': str, 'ts': float}

def _key(channel, marker: str) -> str:
    cid = getattr(channel, "id", None)
    return f"{cid}:{marker}"

def _load():
    global _index
    if os.path.exists(_INDEX_PATH):
        try:
            with open(_INDEX_PATH, "r", encoding="utf-8") as f:
                _index = json.load(f)
        except Exception:
            _index = {}

def _save():
    tmp = _INDEX_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(_index, f, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, _INDEX_PATH)

_load()

async def index(channel, marker: str, message):
    async with _lock:
        _index[_key(channel, marker)] = {"id": message.id, "hash": _index.get(_key(channel, marker), {}).get("hash"), "ts": time.time()}
        _save()

def get_cached_hash(channel, marker: str) -> Optional[str]:
    return _index.get(_key(channel, marker), {}).get("hash")

def set_cached_hash(channel, marker: str, value: Optional[str]):
    async def _set():
        async with _lock:
            ent = _index.get(_key(channel, marker)) or {}
            ent["hash"] = value
            ent["ts"] = time.time()
            _index[_key(channel, marker)] = ent
            _save()
    # fire and forget
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_set())
    except Exception:
        pass

async def fetch_indexed(channel, marker: str):
    ent = _index.get(_key(channel, marker))
    if not ent:
        return None
    try:
        return await channel.fetch_message(ent["id"])
    except NotFound:
        return None
    except Exception:
        return None

async def find_existing(channel, *, title: str, marker: str, search_limit: int = 200):
    # 1) scan pins
    try:
        pins = await channel.pins()
        for m in pins:
            if m.author and getattr(m.author, "bot", False) and m.embeds:
                e0 = m.embeds[0]
                if (e0.title or "") == title and marker in (getattr(e0.footer, "text", "") or ""):
                    return m
    except Exception:
        pass
    # 2) scan recent history
    try:
        async for m in channel.history(limit=search_limit, oldest_first=False):
            if m.author and getattr(m.author, "bot", False) and m.embeds:
                e0 = m.embeds[0]
                if (e0.title or "") == title and marker in (getattr(e0.footer, "text", "") or ""):
                    return m
    except Exception:
        pass
    return None

async def gc_dupes(channel, *, title: str, marker: str, keep: int, search_limit: int = 100):
    """Delete older duplicate sticky messages to avoid clutter.
    Best-effort, ignores errors if lacking perms."""
    try:
        seen = 0
        async for m in channel.history(limit=search_limit, oldest_first=False):
            if m.id == keep: 
                continue
            if m.author and getattr(m.author, "bot", False) and m.embeds:
                e0 = m.embeds[0]
                if (e0.title or "") == title and marker in (getattr(e0.footer, "text", "") or ""):
                    with contextlib.suppress(Exception):
                        await m.unpin()
                    with contextlib.suppress(Exception):
                        await m.delete()
                    seen += 1
        return seen
    except Exception:
        return 0
