\
#!/usr/bin/env bash
# probe_endpoints.sh
# Versi patch: tetap fungsi lama + opsi --with-xp untuk menampilkan XP via curl (tanpa file baru).
set -euo pipefail
: "${BASE:?Set BASE, e.g. https://satpambot-31l5.onrender.com}"
AUTH_HEADER=${AUTH:-}
paths=( "healthz" "get/learning:status" "get/learning:status_json" "api/get/learning:status" "api/get/learning:status_json" "learning/status" "learning:status" )

WITH_XP=0
XP_KEY="${XP_KEY:-xp:bot:senior_total_v2}"

if [[ "${1:-}" == "--with-xp" ]]; then
  WITH_XP=1
  shift || true
fi

echo "BASE=$BASE"
echo "AUTH=${AUTH_HEADER:-<none>}"
echo "----"
for p in "${paths[@]}"; do
  url="$BASE/$p"
  code=$(curl -s -o /dev/null -w "%{http_code}" ${AUTH_HEADER:+-H "$AUTH_HEADER"} "$url")
  echo "$code  $url"
done

if (( WITH_XP == 1 )); then
  if [[ -z "${UPSTASH_REDIS_REST_URL:-}" || -z "${UPSTASH_REDIS_REST_TOKEN:-}" ]]; then
    echo "[xp] UPSTASH_REDIS_REST_URL / TOKEN belum di-set; skip XP" >&2
  else
    echo "----"
    echo "[xp] ${XP_KEY}"
    curl -sS -H "Authorization: Bearer ${UPSTASH_REDIS_REST_TOKEN}" \
         "${UPSTASH_REDIS_REST_URL}/get/${XP_KEY}"; echo
  fi
fi
