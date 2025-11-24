from discord.ext import commands
import logging

log = logging.getLogger(__name__)

class PersonaGetterFallback(commands.Cog):
    """Provide get_active_persona() fallback to avoid AttributeError in overlays relying on PersonaOverlay."""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            import satpambot.bot.modules.discord_bot.cogs.a00_persona_overlay as persona_mod  # noqa: F401
            # try obtain overlay instance if any
        except Exception:
            pass
        # Monkey-patch a safe getter on the bot for downstream users
        if not hasattr(self.bot, "get_active_persona"):
            def _safe_get_active_persona(*args, **kwargs):
                # minimal default persona string
                return "default"
            setattr(self.bot, "get_active_persona", _safe_get_active_persona)
            log.info("[persona-fallback] installed bot.get_active_persona() default")
async def setup(bot):
    await bot.add_cog(PersonaGetterFallback(bot))