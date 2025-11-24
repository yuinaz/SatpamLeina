#!/usr/bin/env bash
set -euo pipefail

# Normalisasi env (buang CRLF, spasi ekor, slash ekor)
export UPSTASH_REDIS_REST_URL="$(printf %s "${UPSTASH_REDIS_REST_URL:-}" | tr -d '\r' | sed -E 's/[[:space:]]+$//; s#/*$##')"
export UPSTASH_REDIS_REST_TOKEN="$(printf %s "${UPSTASH_REDIS_REST_TOKEN:-}" | tr -d '\r' | sed -E 's/[[:space:]]+$//')"

if [ -z "${UPSTASH_REDIS_REST_URL:-}" ] || [ -z "${UPSTASH_REDIS_REST_TOKEN:-}" ]; then
  echo "ERR: UPSTASH_REDIS_REST_URL/TOKEN kosong." >&2
  exit 1
fi

echo "[xp] ensure ladder TK & mark senior_total >= 2000 (via Upstash REST)"

# Set nilai (tanpa pipeline)
curl -sS -X POST "$UPSTASH_REDIS_REST_URL/set/xp:bot:senior_total/2000" \
  -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" >/dev/null

# URL-encode JSON ladder: {"L1":1342,"L2":500}
curl -sS -X POST "$UPSTASH_REDIS_REST_URL/set/xp:ladder:TK/%7B%22L1%22%3A1342%2C%22L2%22%3A500%7D" \
  -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" >/dev/null

# Tampilkan hasil
echo -n "senior_total: "
curl -sS "$UPSTASH_REDIS_REST_URL/get/xp:bot:senior_total" \
  -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN"
echo
echo -n "ladder TK   : "
curl -sS "$UPSTASH_REDIS_REST_URL/get/xp:ladder:TK" \
  -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN"
echo
