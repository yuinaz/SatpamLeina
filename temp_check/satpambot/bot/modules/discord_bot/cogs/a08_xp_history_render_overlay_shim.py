\
from __future__ import annotations
import logging
try:
    from satpambot.bot.modules.discord_bot.cogs.a08_xp_history_render_overlay import award_xp as _award
except Exception:
    _award=None
log=logging.getLogger(__name__)
async def award_xp(delta:int=0):
    if callable(_award): return await _award(delta)
    return False
