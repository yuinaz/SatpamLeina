from __future__ import annotations

from discord.ext import commands

# satpambot/bot/modules/discord_bot/cogs/selfheal_learning_bridge.py
import logging

log = logging.getLogger(__name__)

SCORE_PER_OP = {
    "set_cfg": 1,
    "reload_extension": 2,
    "send_log": 0,
}

class SelfhealLearningBridge(commands.Cog):
    """Naikkan progres TK–SD (atau SMP–S3 jika ada) tiap aksi self-heal berhasil."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Event dari selfheal_groq_agent: bot.dispatch("selfheal_action_applied", act, ok, msg)
    @commands.Cog.listener()
    async def on_selfheal_action_applied(self, act, ok: bool, msg: str):
        if not ok:
            return
        delta = SCORE_PER_OP.get(str(act.get("op")), 0)
        if delta <= 0:
            return
        # Prioritas: Junior (TK–SD) → Senior (SMP–S3)
        policy = self.bot.get_cog("JuniorLearningPolicy")
        if policy and hasattr(policy, "bump_first_incomplete"):
            target = policy.bump_first_incomplete(delta=delta)
            if target:
                log.info("[bridge] bump junior: %s +%s", target, delta)
                return
        senior = self.bot.get_cog("SeniorLearningPolicy")
        if senior and hasattr(senior, "update_metric"):
            # heuristik: cari level pertama yg belum 100%
            for phase, levels in getattr(senior, "db", {}).items():
                for name, score in levels.items():
                    if int(score) < 100:
                        senior.update_metric(phase, name, delta=delta)
                        log.info("[bridge] bump senior: %s-%s +%s", phase, name, delta)
                        return
async def setup(bot: commands.Bot):
    await bot.add_cog(SelfhealLearningBridge(bot))