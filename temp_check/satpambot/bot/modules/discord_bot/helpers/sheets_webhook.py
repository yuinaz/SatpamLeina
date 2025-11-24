import os, aiohttp
from .metrics_agg import now_iso

SHEETS_WEBHOOK_URL = os.getenv("SHEETS_WEBHOOK_URL", "")
SHEETS_TOKEN = os.getenv("SHEETS_TOKEN", "")

async def post_to_sheets(payload: dict):
    if not SHEETS_WEBHOOK_URL or not SHEETS_TOKEN:
        return  # Not configured; silently skip
    payload = dict(payload)
    payload["token"] = SHEETS_TOKEN
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.post(SHEETS_WEBHOOK_URL, json=payload, timeout=15) as r:
                await r.text()
    except Exception:
        # ignore network errors (free plan stability)
        pass

async def log_system_metrics(guild_id=None, metrics: dict | None = None):
    metrics = metrics or {}
    await post_to_sheets({
        "sheet": "SystemMetrics",
        "type": "system_metrics",
        "timestamp": now_iso(),
        "guild_id": guild_id or "",
        **metrics
    })

async def log_command(guild_id, user_id, command, status, duration_ms=""):
    await post_to_sheets({
        "sheet": "Commands",
        "type": "command",
        "timestamp": now_iso(),
        "guild_id": guild_id or "",
        "user_id": user_id or "",
        "command": command or "",
        "status": status,
        "duration_ms": duration_ms,
    })

async def log_moderation_ban(guild_id, target_id, moderator_id="", reason=""):
    await post_to_sheets({
        "sheet": "Bans",
        "type": "moderation",
        "timestamp": now_iso(),
        "guild_id": guild_id or "",
        "target_id": target_id or "",
        "action": "ban",
        "moderator_id": moderator_id or "",
        "reason": reason or "",
    })

async def log_moderation_unban(guild_id, target_id, moderator_id="", reason=""):
    await post_to_sheets({
        "sheet": "Bans",
        "type": "moderation",
        "timestamp": now_iso(),
        "guild_id": guild_id or "",
        "target_id": target_id or "",
        "action": "unban",
        "moderator_id": moderator_id or "",
        "reason": reason or "",
    })
