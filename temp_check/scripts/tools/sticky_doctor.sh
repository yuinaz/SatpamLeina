#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COGS_DIR="$ROOT/satpambot/bot/modules/discord_bot/cogs"
LOADER="$ROOT/satpambot/bot/modules/discord_bot/cogs_loader.py"
APP_DASH="$ROOT/satpambot/dashboard/app_dashboard.py"
APP_FALL="$ROOT/satpambot/dashboard/app_fallback.py"
ENV_LOCAL="$ROOT/.env.local"
PATCH_PY="$ROOT/scripts/patch_healthz.py"

HARD=0
FIX=0
for arg in "$@"; do
  case "$arg" in
    --hard) HARD=1 ;;
    --fix)  FIX=1 ;;
  esac
done

echo "== Sticky Doctor v4 (Git Bash) =="
echo "ROOT=$ROOT"

echo
echo "[1] Scan sticky cogs:"
shopt -s nullglob
STICKY_FILES=( "$COGS_DIR"/*sticky*.py )
for f in "${STICKY_FILES[@]}"; do echo "  - $(basename "$f")"; done
count=${#STICKY_FILES[@]}
if (( count == 0 )); then echo "  (none)"; fi

echo
echo "[2] Loader DISABLED_COGS:"
if [[ -f "$LOADER" ]]; then
  CURRENT=$(grep -Eo 'DISABLED_COGS\s*=\s*set\(\(os\.getenv\("DISABLED_COGS"\)\s*or\s*".*"\)\.split\(",\"\)\)\)' "$LOADER" || true)
  echo "  -> ${CURRENT:-'(not found)'}"
fi

patch_loader() {
  local file="$1"
  if grep -q 'DISABLED_COGS' "$file"; then
    perl -0777 -pe 's/DISABLED_COGS\s*=\s*set\(\(os\.getenv\("DISABLED_COGS"\)\s*or\s*".*?"\)\.split\(",\"\)\)\)/DISABLED_COGS = set((os.getenv("DISABLED_COGS") or "image_poster,sticky_guard,status_sticky_patched").split(","))/' -i.bak "$file"
    echo "  -> Patched loader default; backup at ${file}.bak"
  else
    printf '\n# Default-disable legacy sticky cogs\nDISABLED_COGS = set((os.getenv("DISABLED_COGS") or "image_poster,sticky_guard,status_sticky_patched").split(","))\n' >> "$file"
    echo "  -> Appended default to $file"
  fi
}

hard_disable_files() {
  local f
  for f in "$COGS_DIR/status_sticky_patched.py" "$COGS_DIR/sticky_guard.py"; do
    if [[ -f "$f" ]]; then
      mv -f "$f" "${f}.disabled"
      echo "  -> Renamed $(basename "$f") -> $(basename "${f}.disabled")"
    fi
  done
}

ensure_env_local() {
  local line='DISABLED_COGS=image_poster,sticky_guard,status_sticky_patched'
  if [[ -f "$ENV_LOCAL" ]]; then
    if grep -q '^DISABLED_COGS=' "$ENV_LOCAL"; then
      perl -0777 -pe 's/^DISABLED_COGS=.*/DISABLED_COGS=image_poster,sticky_guard,status_sticky_patched/m' -i "$ENV_LOCAL"
    else
      echo "$line" >> "$ENV_LOCAL"
    fi
  else
    echo "$line" > "$ENV_LOCAL"
  fi
  echo "  -> Wrote $ENV_LOCAL"
}

if [[ "$FIX" -eq 1 ]]; then
  echo
  echo "[3] Apply fixes:"
  [[ -f "$LOADER" ]] && patch_loader "$LOADER"
  ensure_env_local
  if [[ -f "$APP_DASH" ]]; then python "$PATCH_PY" "$APP_DASH"; fi
  if [[ -f "$APP_FALL" ]]; then python "$PATCH_PY" "$APP_FALL"; fi
  if [[ "$HARD" -eq 1 ]]; then hard_disable_files; fi
fi

echo
echo "[4] Summary:"
if [[ -f "$ENV_LOCAL" ]]; then head -n1 "$ENV_LOCAL"; fi
echo "Done. Restart services."
