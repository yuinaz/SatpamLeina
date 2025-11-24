from discord.ext import commands

import os, logging, importlib

log = logging.getLogger(__name__)

def _phase_from_bot(bot):
    try:
        st = getattr(bot, "_xp_state", {}) or {}
        return (st.get("phase") or os.getenv("LEARNING_PHASE_DEFAULT","tk")).lower()
    except Exception:
        return os.getenv("LEARNING_PHASE_DEFAULT","tk").lower()

def _segment_pick(total, items):
    total = int(total or 0)
    for name, cost in items:
        cost = int(cost or 0)
        if total < cost:
            return name, total, cost - total, False
        total -= cost
    return items[-1][0], items[-1][1], 0, True

class LadderSegmentMode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if os.getenv("LADDER_MODE","").lower() not in ("segment","segments","per_level","per-level","delta"):
            log.info("[ladder-segment] LADDER_MODE not 'segment' – skip")
            return
        try:
            m = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.learning_passive_observer")
        except Exception as e:
            log.warning("[ladder-segment] import fail: %r", e); 
            return

        def compute_label_segment(total_xp, ladder_map, phase=None):
            ph = (phase or _phase_from_bot(self.bot)).lower()
            groups = ladder_map.get(ph) if isinstance(ladder_map, dict) else None
            if not groups:
                return "TK-L1"
            running = int(total_xp or 0)
            for group_name, levels in groups.items():  # JSON order preserved
                items = list(levels.items())
                if not items: 
                    continue
                lvl, spent, left, finished = _segment_pick(running, items)
                if finished:
                    running -= sum(v for _,v in items)
                    continue
                label = f"{group_name}-{lvl}"
                log.debug("[ladder-segment] total=%s -> %s (left_in_level=%s)", total_xp, label, left)
                return label
            try:
                last_group, last_levels = list(groups.items())[-1]
                last_level = list(last_levels.items())[-1][0]
                return f"{last_group}-{last_level}"
            except Exception:
                return "TK-L1"

        setattr(m, "compute_label_from_group", compute_label_segment)
        log.info("[ladder-segment] compute_label_from_group = segment-mode")

async def setup(bot):
    await bot.add_cog(LadderSegmentMode(bot))