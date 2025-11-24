
# a00_yaml_log_quieter_overlay.py
from discord.ext import commands
import logging

class YamlLogQuieter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # Demote specific noisy loggers to DEBUG when yaml is missing
        noisy = [
            "satpambot.bot.modules.discord_bot.cogs.a02_autolearn_yaml_hooks_overlay",
            "satpambot.bot.modules.discord_bot.cogs.a02_selfheal_yaml_hooks_overlay",
            "satpambot.bot.modules.discord_bot.cogs.a00_config_hotreload_overlay",
        ]
        for name in noisy:
            lg = logging.getLogger(name)
            lg.setLevel(logging.DEBUG)
async def setup(bot):
    await bot.add_cog(YamlLogQuieter(bot))