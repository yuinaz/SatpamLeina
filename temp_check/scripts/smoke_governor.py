# /mnt/data/scripts/smoke_governor.py
import importlib
mods = [
    "satpambot.ai.resource_governor",
    "satpambot.bot.modules.discord_bot.cogs.neuro_governor",
]
for m in mods:
    try:
        importlib.import_module(m)
        print(f"[OK] import: {m}")
    except Exception as e:
        print(f"[FAIL] {m}: {e}")
