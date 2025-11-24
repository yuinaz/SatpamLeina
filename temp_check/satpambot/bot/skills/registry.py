
"""
skills/registry.py
- Simple in-process skill registry for Leina (Render Free)
- Usage:
    from satpambot.bot.skills.registry import skill, get, all_skills
    @skill("ping") async def ping(ctx, **kw): return "pong"
"""
import asyncio, logging
from typing import Callable, Dict, Awaitable

log = logging.getLogger(__name__)
_REG: Dict[str, Callable[..., Awaitable]] = {}

def skill(name: str):
    def dec(fn: Callable[..., Awaitable]):
        _REG[name] = fn
        log.info("[skill] registered: %s", name)
        return fn
    return dec

def get(name: str): return _REG.get(name)
def all_skills(): return sorted(_REG.keys())

async def call(name: str, *args, **kwargs):
    fn = get(name)
    if not fn: 
        return None
    try:
        return await fn(*args, **kwargs)
    except Exception as e:
        log.warning("[skill:%s] failed: %r", name, e)
        return None
