#!/usr/bin/env bash
set -euo pipefail
: "${UPSTASH_REDIS_REST_URL:?missing}"
: "${UPSTASH_REDIS_REST_TOKEN:?missing}"
KEY="xp:bot:senior_total"
HDR=(-H "Authorization: Bearer ${UPSTASH_REDIS_REST_TOKEN}")
echo "[check] GET ${KEY}"
RES=$(curl -sS "${UPSTASH_REDIS_REST_URL}/get/${KEY}" "${HDR[@]}")
echo "$RES"
VAL=$(printf "%s" "$RES" | grep -o '"senior_total_xp":[[:space:]]*[0-9]\+' | grep -o '[0-9]\+' | head -n1 || true)
if [[ -n "${VAL}" ]]; then
  echo "[fix] SET ${KEY} -> ${VAL}"
  curl -sS -X POST "${UPSTASH_REDIS_REST_URL}/set/${KEY}/${VAL}" "${HDR[@]}"
  echo
else
  echo "[ok] Already integer or legacy JSON not found."
fi
