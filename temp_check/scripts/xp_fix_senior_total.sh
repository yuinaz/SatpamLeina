#!/usr/bin/env bash
# scripts/xp_fix_senior_total.sh
set -euo pipefail

: "${UPSTASH_REDIS_REST_URL:?missing}"
: "${UPSTASH_REDIS_REST_TOKEN:?missing}"

KEY="xp:bot:senior_total"
HDR=(-H "Authorization: Bearer ${UPSTASH_REDIS_REST_TOKEN}")

echo "[check] GET ${KEY}"
RES=$(curl -sS "${UPSTASH_REDIS_REST_URL}/get/${KEY}" "${HDR[@]}")
echo "$RES"

RAW=$(python - <<'PY'
import sys, json
data=json.load(sys.stdin)
print(data.get("result",""))
PY
<<< "$RES")

if [[ "$RAW" =~ ^-?[0-9]+$ ]]; then
  echo "[ok] Already integer: ${RAW}"
  exit 0
fi

FIX=$(python - <<'PY'
import json,sys
raw=sys.stdin.read().strip()
try:
    obj=json.loads(raw)
    if isinstance(obj, dict) and "senior_total_xp" in obj:
        print(int(obj["senior_total_xp"]))
    else:
        print("")
except Exception:
    print("")
PY
<<< "$RAW")

if [[ -n "${FIX}" ]]; then
  echo "[fix] SET ${KEY} -> ${FIX}"
  curl -sS -X POST "${UPSTASH_REDIS_REST_URL}/set/${KEY}/${FIX}" "${HDR[@]}"
  echo
else
  echo "[warn] Cannot coerce value: ${RAW}"
  exit 2
fi
