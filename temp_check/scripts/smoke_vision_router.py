import importlib
importlib.import_module("satpambot.bot.modules.discord_bot.cogs.a00_overlay_bootstrap")
from satpambot.config.runtime import cfg
from satpambot.ml.vision_router import answer
print("== vision provider ==", cfg("VISION_PROVIDER"))
print(answer(b"\x89PNG\r\n", "describe this image")[:200], "...")
print("OK")
