from __future__ import annotations
from discord.ext import commands

import os, json
from pathlib import Path
from datetime import datetime, timezone, timedelta

TK_FILE = Path("data/learn/tk_xp.json")
DEFAULT_KEY = "xp:bot:tk_total"

def _load_tk_file():
    if TK_FILE.exists():
        try:
            return json.loads(TK_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"tk_total_xp": 0, "levels": {}, "last_update": None}

def _try_upstash_get():
    if os.getenv("KV_BACKEND") != "upstash_rest":
        return None, "KV_BACKEND!=upstash_rest"
    url = os.getenv("UPSTASH_REDIS_REST_URL")
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    key = os.getenv("TK_XP_KEY", DEFAULT_KEY)
    if not url or not token:
        return None, "Missing Upstash URL/TOKEN"
    try:
        import requests
        r = requests.get(url.rstrip("/") + "/get/" + key, headers={"Authorization": f"Bearer {token}"}, timeout=8)
        if r.status_code == 200 and r.text:
            return r.text, None
        return None, f"HTTP {r.status_code}"
    except Exception:
        import urllib.request
        req = urllib.request.Request(url.rstrip("/") + "/get/" + key, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            txt = resp.read().decode("utf-8","ignore")
            return txt, None

def get_tk_total_xp() -> int:
    txt, err = _try_upstash_get()
    if txt:
        try:
            obj = json.loads(txt)
            return int(obj.get("tk_total_xp", 0))
        except Exception:
            try:
                return int(txt.strip())
            except Exception:
                pass
    obj = _load_tk_file()
    return int(obj.get("tk_total_xp", 0))

class TKXPOverlay(commands.Cog):
    """Overlay untuk TK: set progress.json berdasarkan TK-only XP store."""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            from satpambot.bot.modules.discord_bot.cogs import a20_curriculum_tk_sd as c
            tz = int(getattr(c, "DEFAULT_CFG", {}).get("tz_offset_minutes", 420))
            def _now_local():
                return datetime.now(timezone.utc) + timedelta(minutes=tz)
            day_key = _now_local().strftime("%Y-%m-%d")
            week_key = _now_local().strftime("%Y-W%W")
            month_key = _now_local().strftime("%Y-%m")
            xp = get_tk_total_xp()
            obj = {"xp_total": xp, "today": day_key, "daily": {day_key: xp}, "weekly": {week_key: xp}, "monthly": {month_key: xp}}
            p = Path(getattr(c, "PROGRESS_FILE"))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("[TKXPOverlay] failed to write TK progress: %r", e)

async def setup(bot):
    await bot.add_cog(TKXPOverlay(bot))