from __future__ import annotations

import os
import time
import hmac
import json
import hashlib
import asyncio
from typing import Any, Dict, Optional, Set

from flask import Blueprint, request, jsonify

def _get_bot():
    try:
        from satpambot.bot.modules.discord_bot.discord_bot import bot
        return bot
    except Exception:
        return None

def _run_coro(coro):
    bot = _get_bot()
    if not bot or not getattr(bot, "loop", None):
        raise RuntimeError("Bot not ready")
    fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
    return fut.result(timeout=8.0)

def _auth_ok(shared: str) -> bool:
    if not shared:
        return False
    auth = request.headers.get("X-Auth", "")
    if auth.startswith("Bearer ") and auth.split(" ", 1)[1] == shared:
        return True
    xs = request.headers.get("X-Sign", "")
    xt = request.headers.get("X-Ts", "")
    if xs and xt:
        try:
            ts = int(xt)
            if abs(time.time() - ts) > 300:
                return False
            raw = (request.method + "\n" + request.path + "\n" + (request.get_data() or b"").decode("utf-8") + "\n" + xt).encode("utf-8")
            sig = hmac.new(shared.encode("utf-8"), raw, hashlib.sha256).hexdigest()
            return hmac.compare_digest(sig, xs)
        except Exception:
            return False
    return False

def make_api_blueprint(shared_token: Optional[str] = None) -> Blueprint:
    bp = Blueprint("bot_internal_api", __name__)

    @bp.before_request
    def _check_auth():
        token = shared_token or os.getenv("SHARED_DASH_TOKEN", "")
        if not _auth_ok(token):
            return jsonify({"ok": False, "error": "unauthorized"}), 401

    @bp.get("/guilds")
    def guilds():
        bot = _get_bot()
        if not bot:
            return jsonify([])
        ids: Set[str] = {str(g.id) for g in bot.guilds}
        return jsonify(sorted(ids))

    @bp.get("/guilds/<gid>/status")
    def guild_status(gid: str):
        bot = _get_bot()
        if not bot or not gid.isdigit():
            return jsonify({"ok": False}), 404
        g = bot.get_guild(int(gid))
        if not g:
            return jsonify({"ok": False}), 404
        st = {
            "id": str(g.id),
            "name": g.name,
            "member_count": getattr(g, "member_count", None),
            "channels": [{"id": str(c.id), "name": getattr(c, "name", "")} for c in g.text_channels],
        }
        return jsonify({"ok": True, "status": st})

    @bp.post("/guilds/<gid>/say")
    def guild_say(gid: str):
        data = request.get_json(silent=True) or {}
        channel_id = str(data.get("channel_id") or "").strip()
        content = str(data.get("content") or "").strip() or "Halo dari Dashboard!"
        if not gid.isdigit():
            return jsonify({"ok": False, "error": "bad gid"}), 400

        async def _send():
            bot = _get_bot()
            g = bot.get_guild(int(gid)) if bot else None
            if not g:
                raise RuntimeError("guild not found")
            ch = g.get_channel(int(channel_id)) if channel_id.isdigit() else g.system_channel
            if not ch:
                ch = next((c for c in g.text_channels if c.permissions_for(g.me).send_messages), None)
            if not ch:
                raise RuntimeError("no accessible text channel")
            await ch.send(content)
            return True

        try:
            _run_coro(_send())
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 400

    return bp