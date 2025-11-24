
from __future__ import annotations
import os, time, logging, types
from typing import Optional, Tuple
import discord
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except Exception:
        return default

def _env_bool(key: str, default: bool=False) -> bool:
    v = os.getenv(key)
    if v is None: return default
    return str(v).strip().lower() in {"1","true","yes","on"}

def _qna_channel_id() -> int:
    for k in ("LEARNING_QNA_CHANNEL_ID","QNA_ISOLATION_CHANNEL_ID","QNA_CHANNEL_ID"):
        v = os.getenv(k)
        if v and str(v).isdigit():
            return int(v)
    return 0

_COOLDOWN_TRACK = {}

def _iso_cooldown_ok(stub) -> Tuple[bool, int]:
    sec = _env_int("QNA_ISOLATION_COOLDOWN_SEC", 180)
    ch_id = getattr(getattr(stub, "channel", None), "id", 0) or 0
    now = time.time()
    last = _COOLDOWN_TRACK.get(ch_id, 0.0)
    remain = int(max(0.0, sec - (now - last)))
    if remain > 0:
        return False, remain
    _COOLDOWN_TRACK[ch_id] = now
    return True, 0

class NeuroAutolearnModeratedV2(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.enable = _env_bool("QNA_ENABLE", True)
        self.interval = max(30, _env_int("QNA_INTERVAL_MIN", 180))
        if self.enable:
            self.qna_loop.change_interval(seconds=self.interval)
            self.qna_loop.start()

    async def _get_qna_channel(self) -> Optional[discord.abc.Messageable]:
        ch_id = _qna_channel_id()
        if not ch_id:
            return None
        ch = self.bot.get_channel(ch_id)
        if ch is None:
            try:
                ch = await self.bot.fetch_channel(ch_id)
            except Exception:
                ch = None
        return ch if isinstance(ch, (discord.TextChannel, discord.Thread)) else None

    @tasks.loop(seconds=180)
    async def qna_loop(self):
        try:
            await self._one_round()
        except Exception as e:
            log.warning("[neuro] qna_loop soft-fail: %s", e)

    async def _one_round(self):
        if not self.enable:
            return
        ch = await self._get_qna_channel()
        if not isinstance(ch, (discord.TextChannel, discord.Thread)):
            log.warning("QNA: channel not found or invalid. Set QNA_CHANNEL_ID or QNA_CHANNEL_NAME.")
            return
        stub = types.SimpleNamespace(channel=types.SimpleNamespace(id=getattr(ch, 'id', 0)))
        _ok, _remain = _iso_cooldown_ok(stub)
        if not _ok:
            return  # honor cooldown silently

        # Ask a question from topics (placeholder — the real logic may live in another cog)
        try:
            return  # disabled placeholder ping; only embed QnA allowed
        except Exception as e:
            log.debug("[neuro] send failed: %s", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(NeuroAutolearnModeratedV2(bot))
