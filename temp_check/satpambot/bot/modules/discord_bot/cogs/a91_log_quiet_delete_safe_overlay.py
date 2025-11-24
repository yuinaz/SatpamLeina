# -*- coding: utf-8 -*-
from discord.ext import commands
import os, logging, asyncio

LV={"DEBUG":10,"INFO":20,"WARNING":30,"ERROR":40,"CRITICAL":50}
class Quiet(commands.Cog):
    def __init__(self,bot): self.bot=bot; self.lv=LV.get((os.getenv("DELETE_SAFE_LOG_LEVEL","WARNING") or "WARNING").upper(),30)
    @commands.Cog.listener()
    async def on_ready(self):
        try:
            import importlib
            mod=importlib.import_module("satpambot.bot.modules.discord_bot.cogs.delete_safe_shim_plus")
            logging.getLogger(mod.__name__).setLevel(self.lv)
        except Exception as e:
            logging.getLogger(__name__).warning("[quiet-delete] setLevel fail: %r", e)

async def setup_async(bot): 
    q=Quiet(bot); await bot.add_cog(q)

def setup(bot):
    try:
        loop = asyncio.get_event_loop()
        if loop and loop.is_running():
            return loop.create_task(setup_async(bot))
    except Exception:
        pass
    return asyncio.run(setup_async(bot))