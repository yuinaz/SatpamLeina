from __future__ import annotations

from discord.ext import commands
import os, json, time, logging
from pathlib import Path
from typing import Dict, Any
import discord

from discord import app_commands

log = logging.getLogger(__name__)

BASE = Path(os.getenv("NEURO_BRIDGE_DIR", "data/neuro-lite"))
BASE.mkdir(parents=True, exist_ok=True)
J_PATH = BASE / "bridge_junior.json"
S_PATH = BASE / "bridge_senior.json"
H_PATH = BASE / "bridge_history.json"

_SPLIT = os.getenv("NEURO_BRIDGE_XP_SPLIT", "junior:1,senior:1")
SPLIT = {}
for part in _SPLIT.split(","):
    part = part.strip()
    if not part: continue
    try:
        name, val = part.split(":")
        SPLIT[name.strip()] = max(0, int(val))
    except Exception:
        pass
if not SPLIT: SPLIT = {"junior":1, "senior":1}

def _load_json(p: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not p.exists():
        p.write_text(json.dumps(default, indent=2))
        return default.copy()
    try:
        return json.loads(p.read_text())
    except Exception:
        return default.copy()

def _save_json(p: Path, data: Dict[str, Any]):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))

def _add_xp(target: str, pts: int):
    path = J_PATH if target=="junior" else S_PATH
    d = _load_json(path, {"xp":0, "updated":0})
    d["xp"] = int(d.get("xp",0)) + max(0, int(pts))
    d["updated"] = int(time.time())
    _save_json(path, d)
    return d["xp"]

def _record_history(entry: Dict[str, Any]):
    d = _load_json(H_PATH, {"events":[]})
    ev = d.get("events", [])
    ev.append(entry)
    if len(ev) > 500: ev = ev[-500:]
    d["events"] = ev
    _save_json(H_PATH, d)

class NeuroCurriculumBridge(commands.Cog):
    """Listens to neuro_* events and updates XP store (no public messages)."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        log.info("[bridge] ready; split=%s", SPLIT)

    async def on_neuro_xp(self, payload: Dict[str, Any]):
        try:
            pts = max(0, int(payload.get("points", 0)))
            src = str(payload.get("source", "unknown"))
            ch  = int(payload.get("channel_id", 0))
        except Exception:
            return
        if pts <= 0: return

        total_weight = sum(SPLIT.values()) or 1
        for target, w in SPLIT.items():
            add = int(round(pts * (w/total_weight)))
            if add <= 0: continue
            new_total = _add_xp("junior" if target=="junior" else "senior", add)
            try:
                self.bot.dispatch("neuro_curriculum_progress", {
                    "target": target, "delta": add, "total": new_total, "source": src, "channel_id": ch
                })
            except Exception:
                pass

        _record_history({"t": int(time.time()), "type":"xp", "payload": payload})

    async def on_neuro_memories_added(self, payload: Dict[str, Any]):
        _record_history({"t": int(time.time()), "type":"mems", "payload": payload})

    async def on_neuro_autolearn_summary(self, payload: Dict[str, Any]):
        _record_history({"t": int(time.time()), "type":"summary", "payload": payload})

    @app_commands.command(name="neuro_xp_status", description="Lihat XP junior/senior (ephemeral).")
    async def neuro_xp_status(self, itx: discord.Interaction):
        j = _load_json(J_PATH, {"xp":0,"updated":0})
        s = _load_json(S_PATH, {"xp":0,"updated":0})
        txt = (f"Junior: {j['xp']} XP (upd: {j['updated']})\n"
               f"Senior: {s['xp']} XP (upd: {s['updated']})")
        await itx.response.send_message(txt, ephemeral=True)
async def setup(bot: commands.Bot):
    await bot.add_cog(NeuroCurriculumBridge(bot))