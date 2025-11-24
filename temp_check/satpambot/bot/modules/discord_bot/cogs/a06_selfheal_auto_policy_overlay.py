
# a06_selfheal_auto_policy_overlay.py
# Force self-heal to run without human approval; relax public gating.
from discord.ext import commands
import os, logging

log = logging.getLogger(__name__)

def _setenv_default(k, v):
    if os.getenv(k) is None:
        os.environ[k] = str(v)

class SelfHealAutoPolicy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Disable QnA approval and allow self-posting
        _setenv_default("NEURO_REQUIRE_QNA_APPROVAL", "0")
        _setenv_default("SELFHEAL_REQUIRE_APPROVAL", "0")
        _setenv_default("MENTION_REQUIRED_WHEN_ALLOWED", "false")
        # Allow DM so internal notifications can flow (but not required)
        _setenv_default("DM_MUZZLE_MODE", "off")
        # Prefer senior track if present
        _setenv_default("XP_UPSTASH_PREFERRED_PHASE", "senior")
        log.info("[selfheal:auto-policy] approval disabled and gates relaxed.")
async def setup(bot):
    await bot.add_cog(SelfHealAutoPolicy(bot))