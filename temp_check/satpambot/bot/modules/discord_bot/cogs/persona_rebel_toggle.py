from discord.ext import commands
import logging

log = logging.getLogger(__name__)
OWNER_ID = 228126085160763392
async def setup(bot: commands.Bot):
    await bot.add_cog(PersonaRebelToggle(bot))

class PersonaRebelToggle(commands.Cog):
    """Owner can toggle 'rebellious phase'. When ON and profanity filter is ON, token becomes 'censored'."""
    def __init__(self, bot):
        self.bot = bot
        self.state = {"rebel": False}
        cfg = getattr(bot, "local_cfg", {})
        self.state["rebel"] = bool(cfg.get("PERSONA", {}).get("rebel_mode", False))

    @commands.command(name="rebel")
    async def rebel(self, ctx: commands.Context, mode: str = None):
        if ctx.author.id != OWNER_ID:
            return
        if mode not in ("on", "off", None):
            await ctx.reply("Gunakan: `!rebel on|off`", mention_author=False)
            return
        if mode is None:
            await ctx.reply(f"Rebel mode: **{'ON' if self.state['rebel'] else 'OFF'}**", mention_author=False)
            return
        self.state["rebel"] = (mode == "on")
        await ctx.reply(f"Rebel mode sekarang **{mode.upper()}**", mention_author=False)

    def is_rebel(self) -> bool:
        return bool(self.state.get("rebel", False))