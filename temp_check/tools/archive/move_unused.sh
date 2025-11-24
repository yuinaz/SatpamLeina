#!/usr/bin/env bash
set -euo pipefail
mkdir -p unused
if [ -f 'satpambot/bot/modules/discord_bot/cogs/ban_commands.py' ]; then mv 'satpambot/bot/modules/discord_bot/cogs/ban_commands.py' 'unused/satpambot__bot__modules__discord_bot__cogs__ban_commands.py'; fi
if [ -f 'satpambot/bot/modules/discord_bot/cogs/ban_overrides.py' ]; then mv 'satpambot/bot/modules/discord_bot/cogs/ban_overrides.py' 'unused/satpambot__bot__modules__discord_bot__cogs__ban_overrides.py'; fi
if [ -f 'satpambot/bot/modules/discord_bot/cogs/image_poster.py' ]; then mv 'satpambot/bot/modules/discord_bot/cogs/image_poster.py' 'unused/satpambot__bot__modules__discord_bot__cogs__image_poster.py'; fi
if [ -f 'satpambot/bot/modules/discord_bot/cogs/testban_hybrid.py' ]; then mv 'satpambot/bot/modules/discord_bot/cogs/testban_hybrid.py' 'unused/satpambot__bot__modules__discord_bot__cogs__testban_hybrid.py'; fi
if [ -f 'satpambot/bot/modules/discord_bot/cogs/status_sticky_manual_proxy.py' ]; then mv 'satpambot/bot/modules/discord_bot/cogs/status_sticky_manual_proxy.py' 'unused/satpambot__bot__modules__discord_bot__cogs__status_sticky_manual_proxy.py'; fi
