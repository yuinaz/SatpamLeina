from discord.ext import commands

import os
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

log = logging.getLogger(__name__)

STORE_PATH = Path("satpambot/bot/data/xp_store.json")

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _ensure_store(d):
    if not isinstance(d, dict):
        d = {}
    d.setdefault("version", 2)
    d.setdefault("users", {})
    d.setdefault("awards", {})
    d.setdefault("stats", {})
    d.setdefault("updated_at", _now_iso())
    return d

def _safe_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return int(default)

def _load_store():
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}
    except Exception as e:
        log.warning("[xp-persist] failed to load store (%s), recreating", e)
        data = {}
    data = _ensure_store(data)
    return data

def _save_store(data):
    data = _ensure_store(data)
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STORE_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STORE_PATH)

class XPAwardEventPersistOverlay(commands.Cog):
    """Bridge events -> local file store (and optional external backends handled elsewhere)."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _apply_award(self, user_id, amount, reason=None):
        user_id = str(user_id)
        store = _load_store()
        users = store["users"]
        u = users.get(user_id, {"xp": 0, "awards": []})
        u["xp"] = _safe_int(u.get("xp", 0)) + _safe_int(amount, 1)
        u.setdefault("awards", [])
        u["awards"].append({
            "ts": _now_iso(),
            "amount": _safe_int(amount, 1),
            "reason": reason or "award",
        })
        # keep last 50 awards per user
        u["awards"] = u["awards"][-50:]
        users[user_id] = u
        store["users"] = users
        store["updated_at"] = _now_iso()
        _save_store(store)
        log.info("[xp-persist] +%s -> user=%s total=%s reason=%s",
                 _safe_int(amount, 1), user_id, u["xp"], reason or "-")

    # --- Event listeners (robust to positional/keyword styles) ---
    @commands.Cog.listener()
    async def on_xp_add(self, *args, **kwargs):
        uid = kwargs.get("user_id") or kwargs.get("uid")
        amt = kwargs.get("amount")
        reason = kwargs.get("reason")
        if uid is None and len(args) >= 1:
            uid = args[0]
        if amt is None and len(args) >= 2:
            amt = args[1]
        if reason is None and len(args) >= 3:
            reason = args[2]
        if uid is None or amt is None:
            log.debug("[xp-persist] on_xp_add ignored (bad args) args=%s kwargs=%s", args, kwargs)
            return
        await self._apply_award(uid, amt, reason)

    # some dispatchers may use custom event names like 'satpam_xp' or 'xp.award'
    @commands.Cog.listener()
    async def on_satpam_xp(self, *args, **kwargs):
        return await self.on_xp_add(*args, **kwargs)

    # if someone uses bot.dispatch('xp.award', ...), discord.py will call on_xp_award
    @commands.Cog.listener()
    async def on_xp_award(self, *args, **kwargs):
        return await self.on_xp_add(*args, **kwargs)

async def setup(bot: commands.Bot):
    name = XPAwardEventPersistOverlay.__name__
    if getattr(bot, "cogs", None) and name in bot.cogs:
        log.info("[xp-persist] already loaded, skipping")
        return
    await bot.add_cog(XPAwardEventPersistOverlay(bot))
    log.info("[xp-persist] loaded OK")