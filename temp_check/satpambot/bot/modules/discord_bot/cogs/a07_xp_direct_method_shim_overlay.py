from discord.ext import commands

class XpDirectMethodShim(commands.Cog):
    """Provide direct XP methods so a08_xp_message_awarder_overlay can call them
    instead of falling back to 'dispatch events' (and spamming self-heal warnings).
    Methods:
      - bot.xp_add(member, amount, reason)
      - bot.xp_award(member, amount, reason)  (alias)
      - bot.satpam_xp(member, amount, reason) (alias)
    Internally, we still dispatch the usual events so other cogs keep working.
    """
    def __init__(self, bot):
        self.bot = bot
        # expose as attributes on the bot so other cogs can find them
        setattr(bot, "xp_add", self.xp_add)
        setattr(bot, "xp_award", self.xp_award)
        setattr(bot, "satpam_xp", self.xp_add)

    async def xp_add(self, member, amount: int, reason: str | None = None):
        amt = int(amount)
        # keep event-based pipeline for compatibility
        self.bot.dispatch("xp_add", member, amt, reason or "msg-award")
        self.bot.dispatch("xp.award", member, amt, reason or "msg-award")
        self.bot.dispatch("satpam_xp", member, amt, reason or "msg-award")
        return True

    async def xp_award(self, member, amount: int, reason: str | None = None):
        return await self.xp_add(member, amount, reason)

async def setup(bot):
    await bot.add_cog(XpDirectMethodShim(bot))
    print("[xp-direct-shim] ready — provided xp_add/xp_award/satpam_xp methods")