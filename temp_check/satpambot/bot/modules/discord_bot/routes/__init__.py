# modules/__init__.py
# This file initializes the module package

# Auto-load anti invite NSFW-only cog
try:
    import asyncio
    async def _load_invite_cog(bot):
        try:
            await bot.load_extension("modules.discord_bot.cogs.anti_invite_autoban")
        except Exception:
            pass
    if hasattr(globals(), "bot") and isinstance(globals().get("bot"), commands.Bot):
        bot.loop.create_task(_load_invite_cog(globals()["bot"]))
except Exception:
    pass
