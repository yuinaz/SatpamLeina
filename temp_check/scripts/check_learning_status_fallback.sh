#!/usr/bin/env bash
# check_learning_status_fallback.sh (hotfix 2025-10-24)
# - Mode default: cek learning:status via HTTP kalau BASE tersedia; jika tidak, langsung fallback Upstash.
# - Mode --check-xp: cek kenaikan XP & (opsional) grep provider, tanpa ketergantungan BASE.

set -euo pipefail

XP_KEY="${XP_KEY:-xp:bot:senior_total_v2}"
EXPECTED_DELTA="${EXPECTED_DELTA:-5}"
TIMEOUT_SEC="${TIMEOUT_SEC:-120}"
SLEEP_SEC="${SLEEP_SEC:-5}"
GREPK="${GREPK:-'(groq|gemini)'}"

usage() {
  cat <<USG
Usage:
  bash scripts/check_learning_status_fallback.sh [--check-xp] [--log /path/to/bot.log]
USG
}

say(){ printf "%s\n" "$*" >&2; }

need_env() { local k="$1"; [[ -n "${!k:-}" ]] || { say "[env] $k belum diset"; return 1; }; }

get_upstash(){
  local key="$1"
  local url="$UPSTASH_REDIS_REST_URL/get/$key"
  curl -sS -H "Authorization: Bearer ${UPSTASH_REDIS_REST_TOKEN}" "$url"
}

parse_xp_value(){
  local raw="$1"
  if command -v jq >/dev/null 2>&1; then
    local v; v=$(printf "%s" "$raw" | jq -r '.result' 2>/dev/null || echo "")
    if [[ "$v" =~ ^[0-9]+$ ]]; then echo "$v"; return; fi
    if [[ "$v" =~ ^\{.*\}$ ]]; then
      echo "$v" | jq -r '..|.senior_total_xp? // empty' | head -n1; return
    fi
  fi
  echo "$raw" | grep -Eo '[0-9]+' | tail -n1
}

get_xp(){ parse_xp_value "$(get_upstash "$XP_KEY")"; }

do_check_xp(){
  need_env UPSTASH_REDIS_REST_URL || exit 2
  need_env UPSTASH_REDIS_REST_TOKEN || exit 2
  say "== XP CHECK (key=${XP_KEY}) =="
  local before after diff start now
  before="$(get_xp || true)"
  if [[ -z "$before" ]]; then say "[xp] gagal membaca nilai awal"; exit 2; fi
  say "[xp] sebelum: ${before}"
  say ">>> Trigger 1 QnA sampai Answer (embed) muncul di channel QNA..."
  say ">>> Menunggu XP naik >= ${EXPECTED_DELTA} (timeout ${TIMEOUT_SEC}s)"

  start=$(date +%s)
  while :; do
    after="$(get_xp || true)"
    if [[ -n "$after" ]]; then
      diff=$(( after - before ))
      say "[xp] sekarang: ${after} (Δ=${diff})"
      if (( diff >= EXPECTED_DELTA )); then
        say "[xp] ✅ OK — XP bertambah >= ${EXPECTED_DELTA}"; break
      fi
    fi
    now=$(date +%s)
    if (( now - start >= TIMEOUT_SEC )); then
      say "[xp] ❌ Timeout — XP belum naik cukup"; break
    fi
    sleep "${SLEEP_SEC}"
  done
}

do_grep(){
  local file="$1"
  if [[ -z "$file" || ! -f "$file" ]]; then
    say "[grep] LOG_FILE kosong/tidak ditemukan; lewati"; return 0
  fi
  say "== GREP PROVIDER (${file}) =="
  say "[grep] pola: ${GREPK}"
  tail -n 500 "$file" | grep -Ei --color=never "${GREPK}" | tail -n 50 || true
  local g1 g2
  g1=$(tail -n 500 "$file" | grep -Eic "groq" || echo 0)
  g2=$(tail -n 500 "$file" | grep -Eic "gemini|googleai" || echo 0)
  say "  - GROQ  : ${g1} baris"
  say "  - GEMINI: ${g2} baris"
}

do_legacy_status(){
  local had_base=1
  if [[ -z "${BASE:-}" ]]; then
    had_base=0
  fi
  AUTH_HEADER=${AUTH:-}
  local candidates=( "get/learning:status" "get/learning:status_json" "api/get/learning:status" "api/get/learning:status_json" "learning/status" "learning:status" )
  local found=""
  if (( had_base == 1 )); then
    for p in "${candidates[@]}"; do
      url="$BASE/$p"
      code=$(curl -s -o /dev/null -w "%{http_code}" ${AUTH_HEADER:+-H "$AUTH_HEADER"} "$url" || true)
      if [[ "$code" == "200" ]]; then found="$p"; break; fi
    done
  fi
  if [[ -n "$found" ]]; then
    say "[HTTP] $BASE/$found"
    curl -s ${AUTH_HEADER:+-H "$AUTH_HEADER"} "$BASE/$found"; echo
  else
    say "[Fallback Upstash] membaca learning:status & learning:status_json"
    need_env UPSTASH_REDIS_REST_URL || { say "[skip] set BASE atau UPSTASH var untuk fallback"; return 0; }
    need_env UPSTASH_REDIS_REST_TOKEN || { say "[skip] set BASE atau UPSTASH var untuk fallback"; return 0; }
    curl -s "$(printf "%s/get/%s" "$UPSTASH_REDIS_REST_URL" "learning:status")" -H "Authorization: Bearer ${UPSTASH_REDIS_REST_TOKEN}"; echo
    curl -s "$(printf "%s/get/%s" "$UPSTASH_REDIS_REST_URL" "learning:status_json")" -H "Authorization: Bearer ${UPSTASH_REDIS_REST_TOKEN}"; echo
    say "[Info XP] senior v2:"
    curl -s "$(printf "%s/get/%s" "$UPSTASH_REDIS_REST_URL" "$XP_KEY")" -H "Authorization: Bearer ${UPSTASH_REDIS_REST_TOKEN}"; echo
  fi
}

CHECK_XP=0
LOG_FILE_ARG=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-xp) CHECK_XP=1; shift ;;
    --log) LOG_FILE_ARG="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) say "[arg] diabaikan: $1"; shift ;;
  esac
done

if (( CHECK_XP == 1 )); then
  do_check_xp
  do_grep "${LOG_FILE_ARG:-${LOG_FILE:-}}"
else
  do_legacy_status
fi
