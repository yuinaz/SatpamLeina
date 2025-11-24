from __future__ import annotations
from discord.ext import commands

import json, asyncio
from pathlib import Path
from typing import Dict
import discord

try:
    from satpambot.config.runtime import cfg, set_cfg
except Exception:
    def cfg(k, d=None): return d
    def set_cfg(k, v): pass

DATA_DIR = Path("data/learn")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "learn_progress_senior.json"

# Senior: SMP 3 LV, SMA 3 LV, KULIAH 8 LV
DEFAULT_CURRICULUM = { "SMP": 3, "SMA": 3, "KULIAH": 8 }
REQUIRED_SCORE = 100

def _load() -> Dict[str, Dict[str,int]]:
    if DB_PATH.exists():
        try: return json.loads(DB_PATH.read_text(encoding='utf-8'))
        except Exception: return {}
    return {}

def _save(db: Dict[str, Dict[str,int]]):
    DB_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding='utf-8')

def _ensure(db: Dict[str, Dict[str,int]]):
    for phase, n in DEFAULT_CURRICULUM.items():
        db.setdefault(phase, {})
        for i in range(1, n+1):
            db[phase].setdefault(f"L{i}", 0)

def _first_incomplete(db: Dict[str, Dict[str,int]]) -> str | None:
    # Urutan: SMP -> SMA -> KULIAH
    for phase in ("SMP", "SMA", "KULIAH"):
        levels = db.get(phase, {})
        for name in sorted(levels.keys(), key=lambda s: (len(s), s)):
            if int(levels.get(name, 0)) < REQUIRED_SCORE:
                return f"{phase}:{name}"
    return None

class SeniorLearningPolicy(commands.Cog):
    """Kurikulum Senior (SMP–SMA–KULIAH). Non-verbose; tidak kirim pesan publik.
    Perintah: /slearn show | /slearn set | /slearn autolock
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = _load()
        _ensure(self.db)
        self.autolock = bool(cfg("SENIOR_AUTOLOCK", False))

    # ===== helpers =====
    def update_metric(self, phase: str, level: str, delta: int = 1):
        self.db.setdefault(phase, {})
        cur = int(self.db[phase].get(level, 0))
        cur = min(REQUIRED_SCORE, cur + int(delta))
        self.db[phase][level] = cur
        _save(self.db)

    def bump_first_incomplete(self, delta: int = 1) -> str | None:
        target = _first_incomplete(self.db)
        if not target: return None
        phase, level = target.split(":")
        self.update_metric(phase, level, delta)
        return f"{phase}-{level}"

    # ===== slash =====
    @commands.hybrid_group(name="slearn", with_app_command=True, description="Senior learning (SMP–SMA–KULIAH)")
    async def srel(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @srel.command(name="show", with_app_command=True)
    @commands.is_owner()
    async def slearn_show(self, ctx: commands.Context):
        db = self.db
        lines = []
        for phase in ("SMP", "SMA", "KULIAH"):
            lv = db.get(phase, {})
            order = sorted(lv.keys(), key=lambda s: (len(s), s))
            pct = [f"{k}={lv.get(k,0)}%" for k in order]
            lines.append(f"**{phase}**: " + (', '.join(pct) if pct else '-'))
        await ctx.reply("\n".join(lines) or "(empty)", mention_author=False)

    @srel.command(name="set", with_app_command=True)
    @commands.is_owner()
    async def slearn_set(self, ctx: commands.Context, phase: str, level: str, score: int):
        phase, level = phase.upper(), level.upper()
        self.update_metric(phase, level, score - int(self.db.get(phase, {}).get(level, 0)))
        await ctx.reply(f"[OK] {phase}-{level}={score}%", mention_author=False)

    @srel.command(name="autolock", with_app_command=True)
    @commands.is_owner()
    async def slearn_autolock(self, ctx: commands.Context, mode: str):
        on = str(mode).lower() in ("1","true","on","ya","y","enable","enabled")
        self.autolock = on; set_cfg("SENIOR_AUTOLOCK", on)
        await ctx.reply(f"[OK] AutoLock={on}", mention_author=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(SeniorLearningPolicy(bot))