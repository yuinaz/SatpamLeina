
from discord.ext import commands
"""
a06_persona_loader_overlay.py
Expose PersonaStore via Cog so other cogs can access it with bot.get_cog("PersonaOverlay")
Commands (optional, text): !persona list / !persona use <name>
"""
import logging

from satpambot.bot.persona.loader import get_store

log = logging.getLogger(__name__)

class PersonaOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.store = get_store()

    def get_active_persona(self):
        return self.store.get_active()

    @commands.command(name="persona_list")
    async def cmd_list(self, ctx):
        names = ", ".join(self.store.list_names()) or "(none)"
        await ctx.send(f"Personas: {names} | active={self.store.get_active_name()}")

    @commands.command(name="persona_use")
    async def cmd_use(self, ctx, name: str):
        ok = self.store.set_active(name)
        await ctx.send("OK" if ok else f"Persona '{name}' not found.")
async def setup(bot):
    await bot.add_cog(PersonaOverlay(bot))

def setup(bot):
    try:
        import asyncio
        if asyncio.get_event_loop().is_running():
            return asyncio.create_task(bot.add_cog(PersonaOverlay(bot)))
    except Exception: pass
    return bot.add_cog(PersonaOverlay(bot))