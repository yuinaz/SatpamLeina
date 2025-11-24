def _get_conf():
    try:
        from satpambot.config.compat_conf import get_conf
        return get_conf
    except Exception:
        try:
            from satpambot.config.runtime_memory import get_conf
            return get_conf
        except Exception:
            def _f(): return {}
            return _f

import json, os
from pathlib import Path
import discord
from satpambot.bot.utils import embed_scribe

def _dir():
    cfg = _get_conf()()
    base = cfg.get("NEURO_LITE_PROGRESS_DIR", "data/neuro-lite")
    Path(base).mkdir(parents=True, exist_ok=True)
    return base

def _load(path, default):
    p = Path(path)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default

def _save(path, data):
    p = Path(path)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)

def _default_junior():
    return {"overall": 0, "TK": {"L1":0,"L2":0}, "SD": {"L1":0,"L2":0,"L3":0,"L4":0,"L5":0,"L6":0}}

def _default_senior():
    return {"overall": 0}

async def award_points_all(bot: discord.Client, n=1, reason="phish-ban"):
    base = _dir()
    jpath = os.path.join(base, "learn_progress_junior.json")
    spath = os.path.join(base, "learn_progress_senior.json")
    j = _load(jpath, _default_junior())
    s = _load(spath, _default_senior())
    j["overall"] = int(j.get("overall", 0)) + int(n)
    s["overall"] = int(s.get("overall", 0)) + int(n)
    _save(jpath, j); _save(spath, s)

    # Update gate/status embed
    desc = (f"[[neuro-lite:gate]] **NEURO-LITE GATE STATUS**\n\n"
            f"- Junior: **{j['overall']:.1f}%**\n"
            f"- Senior: **{s['overall']:.1f}%**\n"
            f"- Rule: Junior must be 100% before Senior unlocks\n"
            f"- Promotion Allowed: {'YES' if j['overall']>=100 else 'NO'}\n"
            f"_Last reward: {reason} (+{n})_")
    e = discord.Embed(title="Neuro-Lite Progress", description=desc, color=0x2ecc71)
    # route to log thread
    cfg = _get_conf()()
    log_id = int(str(cfg.get("LOG_CHANNEL_ID", "0")) or 0)
    ch = bot.get_channel(log_id) if log_id else None
    if ch is None:
        for g in getattr(bot, "guilds", []):
            if g.text_channels:
                ch = g.text_channels[0]; break
    if ch is not None:
        await embed_scribe.upsert(ch, "NEURO_LITE_GATE_STATUS", e, pin=True, bot=bot, route=True)
    return j, s
