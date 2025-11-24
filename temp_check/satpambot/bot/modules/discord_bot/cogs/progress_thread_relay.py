from __future__ import annotations

from discord.ext import commands
import json, logging
from pathlib import Path
import discord

from discord.ext import tasks
from satpambot.config.local_cfg import cfg, cfg_int

log = logging.getLogger(__name__)

def _progress_file() -> Path:
    return Path(cfg("PROGRESS_FILE", "data/neuro-lite/learn_progress_junior.json"))

def _target_channel_id() -> int | None:
    v = cfg_int("PROGRESS_CHANNEL_ID", 0)
    return v or None

def _thread_name() -> str:
    return cfg("PROGRESS_THREAD_NAME", "neuro-lite progress")

def _keeper_marker() -> str:
    return cfg("PROGRESS_KEEPER_MARKER", "<!-- [neuro-lite:memory] -->")

def _safe_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _estimate_level_xp(d: dict) -> tuple[int, int, int]:
    xp = int(d.get("xp") or d.get("xp_total") or 0)
    xp += int(d.get("hour_points") or 0)
    level = int(d.get("level") or 1)
    goal = int(d.get("target") or d.get("goal") or 10000)
    lv = Path("data/neuro-lite/levels.json")
    if lv.exists():
        j = _safe_json(lv).get("junior") or {}
        if isinstance(j, dict):
            level = int(j.get("level") or level or 1)
            xp = int(j.get("xp") or xp)
            goal = max(goal, int(j.get("to_next") or 0))
    return level, xp, goal

def _format_progress(d: dict) -> str:
    lvl, xp_est, goal = _estimate_level_xp(d)
    body = f"Level: **{lvl}**\nXP: **{xp_est}** / {goal}"
    marker = _keeper_marker()
    if marker and marker not in body:
        body = f"{body}\n{marker}"
    return body

async def _find_or_create_thread(ch: discord.TextChannel) -> discord.Thread | None:
    name = _thread_name()
    try:
        async for th in ch.threads():
            if th.name == name:
                return th
    except Exception:
        pass
    try:
        async for th in ch.archived_threads(limit=50):
            if th.name == name:
                return th
    except Exception:
        pass
    try:
        return await ch.create_thread(name=name, auto_archive_duration=10080)
    except Exception:
        return None

async def _find_keeper(thread: discord.Thread) -> discord.Message | None:
    marker = _keeper_marker()
    try:
        pins = await thread.pins()
        for m in pins:
            if marker in (m.content or ""):
                return m
        async for m in thread.history(limit=100):
            if marker in (m.content or ""):
                return m
    except Exception:
        pass
    return None

class ProgressThreadRelay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self._tick.start()
        log.info("[progress_relay] online; ch_id=%s thread='%s' file=%s marker=%s",
                 _target_channel_id(), _thread_name(), _progress_file(), _keeper_marker())

    def cog_unload(self):
        self._tick.cancel()

    @tasks.loop(minutes=3.0)
    async def _tick(self):
        ch_id = _target_channel_id()
        if not ch_id: 
            return
        ch = self.bot.get_channel(ch_id)
        if ch is None:
            try:
                ch = await self.bot.fetch_channel(ch_id)
            except Exception:
                return
        thread = await _find_or_create_thread(ch)
        if thread is None:
            return
        data = _safe_json(_progress_file())
        content = _format_progress(data) if data else "Belum ada progres terekam.\n" + _keeper_marker()
        keeper = await _find_keeper(thread)
        if keeper:
            try:
                await keeper.edit(content=content, suppress=False)
                return
            except Exception:
                keeper = None
        try:
            msg = await thread.send(content=content)
            await msg.pin()
        except Exception:
            pass
async def setup(bot: commands.Bot):
    await bot.add_cog(ProgressThreadRelay(bot))