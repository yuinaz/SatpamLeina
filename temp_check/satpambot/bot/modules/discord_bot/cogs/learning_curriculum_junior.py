from __future__ import annotations

from discord.ext import commands

# satpambot/bot/modules/discord_bot/cogs/learning_curriculum_junior.py
import json, asyncio
from pathlib import Path
from typing import Dict, List

import discord

try:
    from satpambot.config.runtime import cfg, set_cfg
except Exception:
    def cfg(k, d=None): return d
    def set_cfg(k, v): pass

DATA_DIR = Path("data"); DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "learn_progress_junior.json"

DEFAULT_CURRICULUM = { "TK": 2, "SD": 6 }
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
    # TK harus penuh dulu, baru SD
    for phase in ("TK", "SD"):
        levels = db.get(phase, {})
        # natural order L1..Ln
        for name in sorted(levels.keys(), key=lambda s: (len(s), s)):
            if int(levels.get(name, 0)) < REQUIRED_SCORE:
                return f"{phase}:{name}"
    return None

def _all_done(db: Dict[str, Dict[str,int]]) -> bool:
    for phase, levels in db.items():
        for s in levels.values():
            if int(s) < REQUIRED_SCORE:
                return False
    return True

class JuniorLearningPolicy(commands.Cog):
    """TK–SD policy: gate publik terkunci sampai semua level 100% (TK 2, SD 6)."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = _load(); _ensure(self.db); _save(self.db)
        self.autolock = bool(cfg("JUNIOR_AUTOLOCK", True))

    async def cog_load(self):
        if self.autolock:
            await asyncio.sleep(1.0)
            try:
                gate = self.bot.get_cog("PublicChatGate")
                if gate and hasattr(gate, "lock"):
                    await gate.lock(reason="JuniorLearningPolicy autolock: TK–SD belum 100%")
            except Exception:
                pass

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
    @commands.hybrid_group(name="jlearn", with_app_command=True, description="Junior learning (TK–SD)")
    async def jlearn(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @jlearn.command(name="status", with_app_command=True)
    async def jlearn_status(self, ctx: commands.Context):
        total = sum(DEFAULT_CURRICULUM.values())
        done = sum(1 for p in self.db.values() for v in p.values() if int(v) >= REQUIRED_SCORE)
        embed = discord.Embed(title="TK–SD Progress", color=0x1abc9c)
        embed.add_field(name="Selesai", value=f"{done}/{total}", inline=True)
        embed.add_field(name="AutoLock", value=str(self.autolock), inline=True)
        # tampilkan 6 item pending pertama
        pend = [f"{ph}-{lv}:{sc}%" for ph, lv_sc in self.db.items() for lv, sc in lv_sc.items() if int(sc) < REQUIRED_SCORE]
        if pend:
            embed.add_field(name="Pending (sample)", value=", ".join(pend[:6]) + (f" … (+{len(pend)-6})" if len(pend)>6 else ""), inline=False)
        await ctx.reply(embed=embed, mention_author=False)

    @jlearn.command(name="set", with_app_command=True)
    @commands.is_owner()
    async def jlearn_set(self, ctx: commands.Context, phase: str, level: str, score: int):
        phase, level = phase.upper(), level.upper()
        self.update_metric(phase, level, score - int(self.db.get(phase, {}).get(level, 0)))
        await ctx.reply(f"[OK] {phase}-{level}={score}%", mention_author=False)

    @jlearn.command(name="autolock", with_app_command=True)
    @commands.is_owner()
    async def jlearn_autolock(self, ctx: commands.Context, mode: str):
        on = str(mode).lower() in ("1","true","on","ya","y","enable","enabled")
        self.autolock = on; set_cfg("JUNIOR_AUTOLOCK", on)
        await ctx.reply(f"[OK] AutoLock={on}", mention_author=False)
async def setup(bot: commands.Bot):
    await bot.add_cog(JuniorLearningPolicy(bot))