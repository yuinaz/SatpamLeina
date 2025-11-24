#!/usr/bin/env bash
set -euo pipefail
ROOT="$(pwd)"
DST="$ROOT/satpambot/bot/modules/discord_bot/cogs/clearchat.py"
mkdir -p "$(dirname "$DST")"
cp "satpambot/bot/modules/discord_bot/cogs/clearchat.py" "$DST"
echo "Installed clearchat cog -> $DST"
echo "Restart bot untuk apply."
