import logging
def _set(name, lvl): logging.getLogger(name).setLevel(lvl)
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

# Library yg bawel → WARNING
for n in ("discord", "discord.client", "discord.gateway", "discord.http", "aiohttp", "websockets"):
    _set(n, logging.WARNING)

# App kita tetap INFO
_set("satpambot", logging.INFO)
_set("satpambot.bot.modules.discord_bot.cogs", logging.INFO)
