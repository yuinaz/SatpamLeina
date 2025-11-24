
from discord.ext import commands
OWNER_ID = 228126085160763392
async def setup(bot: commands.Bot):
    await bot.add_cog(ProfanityToggle(bot))

class ProfanityToggle(commands.Cog):
    """Owner command to turn profanity filter on/off at runtime (updates in-memory local_cfg)."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="profanity")
    async def profanity(self, ctx: commands.Context, mode: str = None):
        if ctx.author.id != OWNER_ID:
            return
        cfg = getattr(self.bot, "local_cfg", {})
        safety = cfg.setdefault("SAFETY", {})
        if mode not in ("on", "off", None):
            await ctx.reply("Gunakan: `!profanity on|off`", mention_author=False)
            return
        if mode is None:
            cur = safety.get("profanity_filter", "off")
            await ctx.reply(f"Profanity filter saat ini: **{cur}**", mention_author=False)
            return
        safety["profanity_filter"] = mode
        await ctx.reply(f"Profanity filter di-set ke **{mode}**", mention_author=False)