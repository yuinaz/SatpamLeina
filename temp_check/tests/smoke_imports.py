import os, sys, importlib

# Ensure repo root on sys.path (so 'satpambot' is importable when running from tests/)
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

mods = [
    "satpambot.bot.modules.discord_bot.cogs.a00_learning_status_refresh_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a09_presence_from_upstash_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a98_learning_status_guard",
    "satpambot.bot.modules.discord_bot.cogs.a20_curriculum_tk_sd",
    "satpambot.bot.modules.discord_bot.cogs.a08_learning_status_autopin_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a06_upstash_client",
    "satpambot.bot.modules.discord_bot.helpers.upstash_client",
    "satpambot.bot.modules.discord_bot.helpers.ladder_loader",
    "satpambot.bot.modules.discord_bot.helpers.rank_utils",
    "satpambot.bot.modules.discord_bot.helpers.compat_learning_status",
    "satpambot.bot.modules.discord_bot.helpers.discord_state_io",
    "satpambot.bot.utils.xp_state_discord",
    "satpambot.bot.utils.json",
]

for m in mods:
    importlib.import_module(m)

print("OK: imports passed ✅")
