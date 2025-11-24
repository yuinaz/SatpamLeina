#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-}"
if [[ -z "${ROOT}" ]]; then
  if git_root=$(git rev-parse --show-toplevel 2>/dev/null); then
    ROOT="$git_root"
  else
    ROOT="."
  fi
fi

cd "$ROOT"
ROOT="$(pwd)"

# Candidate locations
MODDIR=""
if [[ -d "$ROOT/bot/modules/discord_bot" ]]; then
  MODDIR="$ROOT/bot/modules/discord_bot"
elif [[ -d "$ROOT/modules/discord_bot" ]]; then
  MODDIR="$ROOT/modules/discord_bot"
else
  # Find first match anywhere under ROOT
  MODDIR="$(find "$ROOT" -type d \( -path "*/bot/modules/discord_bot" -o -path "*/modules/discord_bot" \) 2>/dev/null | sort | head -n 1 || true)"
fi

if [[ -z "${MODDIR}" || ! -d "${MODDIR}" ]]; then
  echo "Gagal menemukan folder modules/discord_bot (atau bot/modules/discord_bot) di: $ROOT"
  echo "Tips: jalankan:  find . -type d -path '*/modules/discord_bot' -o -path '*/bot/modules/discord_bot'"
  echo "Atau panggil skrip:  ./run_grep_checks_auto.sh /path/ke/root_repo"
  exit 2
fi

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
fail=0

echo -e "${YELLOW}Root: ${ROOT}${NC}"
echo -e "${YELLOW}Mod dir terdeteksi: ${MODDIR}${NC}\n"

echo -e "${YELLOW}== Check 1: message.delete() di luar utils/actions.py ==${NC}"
out1="$(grep -R -n "message\.delete(" "$MODDIR" 2>/dev/null | grep -v -E "utils/actions\.py" || true)"
if [[ -n "$out1" ]]; then
  echo "$out1"
  echo -e "${RED}Found direct message.delete() (harus diganti delete_message_safe)${NC}"
  fail=1
else
  echo -e "${GREEN}OK: tidak ada${NC}"
fi

echo -e "${YELLOW}\n== Check 2: author.(kick|timeout|ban) di luar mod_guard atau utils/actions.py ==${NC}"
out2="$(grep -R -n -E "author\.(kick|timeout|ban)\(" "$MODDIR" 2>/dev/null | grep -v -E "(mod_guard|utils/actions\.py)" || true)"
if [[ -n "$out2" ]]; then
  echo "$out2"
  echo -e "${RED}Found direct author action (pindahkan ke mod_guard/utils/actions)${NC}"
  fail=1
else
  echo -e "${GREEN}OK: tidak ada${NC}"
fi

echo -e "${YELLOW}\n== Check 3: import dari helpers.log_utils (info) ==${NC}"
grep -R -n -E "from\s+.*helpers\.log_utils\s+import" "$ROOT" 2>/dev/null || true

echo -e "${YELLOW}\n== Check 4: def upsert_status_embed ada ==${NC}"
if [[ -f "$MODDIR/helpers/log_utils.py" ]] && grep -n -E "def[[:space:]]+upsert_status_embed\b" "$MODDIR/helpers/log_utils.py" >/dev/null 2>&1 ; then
  echo -e "${GREEN}OK: def ditemukan${NC}"
else
  echo -e "${RED}TIDAK ditemukan def upsert_status_embed di helpers/log_utils.py${NC}"
  fail=1
fi

echo -e "${YELLOW}\n== Ringkas ==${NC}"
if [[ $fail -eq 0 ]]; then
  echo -e "${GREEN}Semua cek lulus.${NC}"
else
  echo -e "${RED}Ada pelanggaran. Perbaiki lalu jalankan ulang skrip ini.${NC}"
fi

exit $fail
