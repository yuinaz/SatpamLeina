from __future__ import annotations

from discord.ext import commands
import os, json, time, logging
from pathlib import Path
from typing import Dict, Any, List, Tuple
import discord

from discord import app_commands

log = logging.getLogger(__name__)
BASE = Path(os.getenv("NEURO_BRIDGE_DIR", "data/neuro-lite"))
BASE.mkdir(parents=True, exist_ok=True)
LV_PATH = BASE / "levels.json"
J_PATH = BASE / "bridge_junior.json"
S_PATH = BASE / "bridge_senior.json"

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

# thresholds from ENV or default ladder
def _levels_from_env() -> List[int]:
    raw = os.getenv("NEURO_LEVELS", "0,50,150,350,700,1200,2000")
    vals = []
    for s in raw.split(","):
        s = s.strip()
        if not s: continue
        try: vals.append(max(0, int(s)))
        except Exception: pass
    vals = sorted(set(vals))
    if 0 not in vals: vals = [0] + vals
    return vals

def _calc_level(xp: int, thresholds: List[int]) -> Tuple[int, int]:
    lvl = 1
    for i, t in enumerate(thresholds, start=1):
        if xp >= t: lvl = i
        else: break
    next_need = thresholds[lvl] - xp if lvl < len(thresholds) else 0
    return lvl, max(0, next_need)

class NeuroGovernorLevels(commands.Cog):
    """Silent governor: computes level from XP, no public sends."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.thresholds = _levels_from_env()
        self._update_levels_store()

    def _update_levels_store(self):
        j = _load_json(J_PATH, {"xp":0,"updated":0})
        s = _load_json(S_PATH, {"xp":0,"updated":0})
        j_lvl, j_next = _calc_level(int(j.get("xp",0)), self.thresholds)
        s_lvl, s_next = _calc_level(int(s.get("xp",0)), self.thresholds)
        data = {
            "levels": self.thresholds,
            "junior": {"xp": j.get("xp",0), "level": j_lvl, "to_next": j_next, "updated": j.get("updated",0)},
            "senior": {"xp": s.get("xp",0), "level": s_lvl, "to_next": s_next, "updated": s.get("updated",0)},
            "ts": int(time.time()),
        }
        _save_json(LV_PATH, data)

    # listen to internal curriculum progress to recalc
    async def on_neuro_curriculum_progress(self, payload: Dict[str, Any]):
        try:
            self._update_levels_store()
        except Exception:
            log.exception("Failed to update levels store.")

    @app_commands.command(name="neuro_level_status", description="Lihat level junior/senior + sisa XP ke level berikut (ephemeral).")
    async def neuro_level_status(self, itx: discord.Interaction):
        d = _load_json(LV_PATH, {"levels":[], "junior":{"xp":0,"level":1,"to_next":0}, "senior":{"xp":0,"level":1,"to_next":0}})
        desc = (f"Junior — LV {d['junior']['level']} | XP {d['junior']['xp']} | next +{d['junior'].get('to_next',0)}\n"
                f"Senior — LV {d['senior']['level']} | XP {d['senior']['xp']} | next +{d['senior'].get('to_next',0)}\n"
                f"Thresholds: {d.get('levels', [])}")
        await itx.response.send_message(desc, ephemeral=True)

    @app_commands.command(name="neuro_gate_status", description="Status GATE (selalu terkunci untuk publik).")
    async def neuro_gate_status(self, itx: discord.Interaction):
        await itx.response.send_message("GATE: **LOCKED** — tidak ada chat/reply/react publik sampai human-like ready.", ephemeral=True)
async def setup(bot: commands.Bot):
    await bot.add_cog(NeuroGovernorLevels(bot))