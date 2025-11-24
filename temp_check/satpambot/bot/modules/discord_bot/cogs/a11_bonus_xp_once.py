from __future__ import annotations
from discord.ext import commands

import logging, os, json
from pathlib import Path

from satpambot.config.local_cfg import cfg_int
log = logging.getLogger(__name__)
MARK = Path("data/neuro-lite/bonus_applied_satpam_unified_v1.txt")
BONUS = int(cfg_int("PATCH_BONUS_XP", 150) or 150)
def _apply_bonus():
    try:
        if MARK.exists(): return False
        MARK.parent.mkdir(parents=True, exist_ok=True); MARK.write_text("applied", encoding="utf-8")
        p = Path("data/neuro-lite/learn_progress_junior.json")
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            data["overall"] = int(data.get("overall", 0) or 0) + BONUS
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        log.warning("[bonus_xp] failed to apply: %s", e); return False
class PatchBonus(commands.Cog):
    def __init__(self, bot): self.bot = bot
    async def cog_load(self):
        if _apply_bonus(): log.info("[bonus_xp] +%s XP applied (once)", BONUS)
        else: log.info("[bonus_xp] already applied or failed; skipping")
async def setup(bot): await bot.add_cog(PatchBonus(bot))