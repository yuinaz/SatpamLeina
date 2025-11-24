from __future__ import annotations

from discord.ext import commands
import logging, json
from pathlib import Path
import discord
from satpambot.config.local_cfg import cfg, cfg_int

log = logging.getLogger(__name__)
BOT = None
THREAD_ID = 0
LOCAL_PATH = Path(__file__).resolve().parents[5] / "local.json"

def _read_local() -> dict:
    try:
        return json.loads(LOCAL_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _write_local(update: dict) -> dict:
    base = _read_local()
    base.update(update or {})
    tmp = LOCAL_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(LOCAL_PATH)
    return base

async def _ensure_thread(bot: discord.Client):
    global THREAD_ID
    stored = int(_read_local().get("OWNER_NOTIFY_THREAD_ID", 0) or 0)
    base_id = int(cfg_int("OWNER_NOTIFY_CHANNEL_ID", 0) or 0) or int(cfg_int("LOG_CHANNEL_ID", 0) or 0)
    name = str(cfg("OWNER_NOTIFY_THREAD_NAME", "owner-notify") or "owner-notify")
    if THREAD_ID:
        try:
            t = await bot.fetch_channel(THREAD_ID)
            if isinstance(t, discord.Thread):
                return t
        except Exception:
            THREAD_ID = 0
    if stored:
        try:
            t = await bot.fetch_channel(stored)
            if isinstance(t, discord.Thread):
                THREAD_ID = t.id
                return t
        except Exception:
            pass
    if base_id <= 0:
        log.warning("[owner_notify_redirect] base channel id not set")
        return None
    base = bot.get_channel(base_id) or await bot.fetch_channel(base_id)
    if not isinstance(base, discord.TextChannel):
        log.warning("[owner_notify_redirect] base not TextChannel: %r", base)
        return None
    try:
        for t in base.threads:
            if isinstance(t, discord.Thread) and (t.name or "").strip().lower() == name.lower():
                THREAD_ID = t.id
                _write_local({"OWNER_NOTIFY_THREAD_ID": THREAD_ID})
                return t
    except Exception:
        pass
    try:
        t = await base.create_thread(name=name, auto_archive_duration=10080)
        THREAD_ID = t.id
        _write_local({"OWNER_NOTIFY_THREAD_ID": THREAD_ID})
        log.info("[owner_notify_redirect] created thread %s in #%s", t.id, base.id)
        return t
    except Exception as e:
        log.warning("[owner_notify_redirect] create_thread failed: %s", e)
        return None

async def _redirect_to_thread(*, content=None, embed=None, embeds=None, files=None, **kwargs):
    prefix = str(cfg('OWNER_NOTIFY_PREFIX', '') or '').strip()
    if BOT is None:
        return False
    t = await _ensure_thread(BOT)
    if t is None:
        return False
    try:
        kw = {}
        if content is not None:
            kw["content"] = content
        if embed is not None:
            kw["embed"] = embed
        if embeds is not None:
            kw["embeds"] = embeds
        if files is not None:
            kw["files"] = files
        kw.update(kwargs)
        await t.send(**kw)
        return True
    except Exception as e:
        log.warning("[owner_notify_redirect] thread.send failed: %s", e)
        return False

def _wrap_send_on(cls):
    if not hasattr(cls, "send"):
        return
    orig = getattr(cls, "send")
    if getattr(orig, "__owner_redirect_wrapped__", False):
        return
    async def wrapped(self, *args, **kwargs):
        try:
            owner_id = int(cfg_int("OWNER_USER_ID", 0) or 0)
            uid = int(getattr(self, "id", 0))
            if owner_id and uid == owner_id:
                ok = await _redirect_to_thread(*args, **kwargs)
                if ok:
                    return None
        except Exception:
            pass
        return await orig(self, *args, **kwargs)
    setattr(wrapped, "__owner_redirect_wrapped__", True)
    setattr(cls, "send", wrapped)

def _wrap_dmchannel_send():
    try:
        orig = discord.DMChannel.send
    except Exception:
        return
    if getattr(orig, "__owner_redirect_wrapped__", False):
        return
    async def wrapped(self, *args, **kwargs):
        try:
            owner_id = int(cfg_int("OWNER_USER_ID", 0) or 0)
            recipient = getattr(self, "recipient", None)
            uid = int(getattr(recipient, "id", 0) or 0)
            if owner_id and uid == owner_id:
                ok = await _redirect_to_thread(*args, **kwargs)
                if ok:
                    return None
        except Exception:
            pass
        return await orig(self, *args, **kwargs)
    setattr(wrapped, "__owner_redirect_wrapped__", True)
    discord.DMChannel.send = wrapped

class OwnerNotifyRedirect(discord.ext.commands.Cog):
    def __init__(self, bot):
        global BOT
        BOT = bot
    async def cog_load(self):
        _wrap_send_on(discord.User)
        _wrap_send_on(discord.Member)
        _wrap_dmchannel_send()
        log.info("[owner_notify_redirect] wrappers installed; base=%s", cfg_int("OWNER_NOTIFY_CHANNEL_ID", 0) or cfg_int("LOG_CHANNEL_ID", 0))
async def setup(bot):
    await bot.add_cog(OwnerNotifyRedirect(bot))