
from discord.ext import commands
"""
a06_skills_registry_overlay.py
- Exposes skills via Cog and registers a few safe examples.
- Hooks for QnA/Autolearn can import registry.call("skill_name", ...).
"""
import logging

from satpambot.bot.skills.registry import skill, all_skills, call

log = logging.getLogger(__name__)

# --- example skills (safe) ---
@skill("xp_award")
async def _xp_award(bot, user_id: int, amount: int = 1, reason: str = "skill:award"):
    # Fire multiple legacy events safely (ignore errors)
    for ev in ("xp_add", "xp.award", "satpam_xp"):
        try:
            bot.dispatch(ev, int(user_id), int(amount), reason=reason)
        except TypeError:
            try:
                bot.dispatch(ev, int(user_id), int(amount))
            except Exception:
                pass
        except Exception:
            pass
    return {"ok": True, "user_id": int(user_id), "amount": int(amount), "reason": reason}

@skill("list_skills")
async def _list_skills(*_, **__):
    return all_skills()

class SkillsOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="skill")
    async def skill_cmd(self, ctx, name: str, *rest):
        res = await call(name, self.bot, *rest)
        await ctx.send(f"{name}: {res}")
async def setup(bot):
    await bot.add_cog(SkillsOverlay(bot))

def setup(bot):
    try:
        import asyncio
        if asyncio.get_event_loop().is_running():
            return asyncio.create_task(bot.add_cog(SkillsOverlay(bot)))
    except Exception: pass
    return bot.add_cog(SkillsOverlay(bot))