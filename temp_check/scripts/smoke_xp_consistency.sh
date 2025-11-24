#!/usr/bin/env bash
# XP consistency smoke (pure bash+jq, no Python) — v2
set -u

INTERACTIVE=0
if tty -s; then INTERACTIVE=1; fi
finish() {
  if [ "$INTERACTIVE" -eq 1 ]; then
    echo
    read -rp "Selesai. Tekan Enter untuk menutup…"
  fi
}
trap finish EXIT

# Auto-source local env if present
[ -z "${UPSTASH_REDIS_REST_URL:-}" ] && [ -f "./scripts/.env.upstash" ] && . "./scripts/.env.upstash"
[ -z "${UPSTASH_REDIS_REST_TOKEN:-}" ] && [ -f "./scripts/.env.upstash" ] && . "./scripts/.env.upstash"

if [ -z "${UPSTASH_REDIS_REST_TOKEN:-}" ] || [ -z "${UPSTASH_REDIS_REST_URL:-}" ]; then
  echo "[ERR] Env UPSTASH_REDIS_REST_TOKEN / UPSTASH_REDIS_REST_URL belum diset."; exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "[ERR] 'jq' belum terpasang. Install jq dulu."; exit 1
fi

AUTH="Authorization: Bearer ${UPSTASH_REDIS_REST_TOKEN}"
BASE="${UPSTASH_REDIS_REST_URL%/}"

# Fetch both totals & statuses
R=$(curl -s -H "$AUTH" -X POST "$BASE/pipeline" \
  -H 'Content-Type: application/json' \
  -d '[["GET","xp:bot:senior_total"],["GET","xp:bot:senior_total_v2"],["GET","learning:status"],["GET","learning:status_json"]]')

A=$(echo "$R" | jq -r '.[0].result|tonumber? // 0')
B=$(echo "$R" | jq -r '.[1].result|tonumber? // 0')
S=$(echo "$R" | jq -r '.[2].result // ""')
J=$(echo "$R" | jq -r '.[3].result // "{}"')
JLBL=$(echo "$J" | jq -r '.label? // empty')
SLBL=$(printf '%s' "$S" | sed -n 's/^\(KULIAH-[S0-9]\+\).*/\1/p')

NEED_HEAL=0
[[ "$A" -ne "$B" ]] && NEED_HEAL=1
[[ -z "$SLBL" || "$SLBL" != "$JLBL" ]] && NEED_HEAL=1

if [ "$NEED_HEAL" -eq 1 ]; then
  echo "[AUTO-HEAL] memperbaiki mismatch (senior_total & status)…"
  TOT=$(echo "[{\"r\":$A},{\"r\":$B}]" | jq '[.[].r] | max')

  # Compute label/pct/rem using jq only
  STAT=$(jq -nc --argjson total "$TOT" '
    def s_th: [19000,35000,58000,70000,96500,158000,220000,262500];
    def s_nm: ["S1","S2","S3","S4","S5","S6","S7","S8"];
    def idx: ([range(0;8)|select($total >= (s_th[.]))] | (if length==0 then 0 else max end));
    def cur: s_th[idx];
    def nxt: (s_th[idx+1]? // cur);
    def pct0: if nxt<=cur then 100 else ((($total - cur) / (nxt - cur)) * 100) end;
    def pct: ((pct0*10|floor)/10);
    def rem: (if $total < nxt then (nxt - $total) else 0 end);
    def lbl: ("KULIAH-" + (s_nm[idx]));
    {status: (lbl + " (" + (pct|tostring) + "%)"),
     json: ({label:lbl, percent:pct, remaining:rem, senior_total:$total} | tostring)}
  ')
  STATUS_LINE=$(echo "$STAT" | jq -r .status)
  JSON_LINE=$(echo "$STAT" | jq -r .json)

  jq -nc --arg t "$TOT" --arg s "$STATUS_LINE" --arg j "$JSON_LINE" '[
    ["SET","xp:bot:senior_total",$t],
    ["SET","xp:bot:senior_total_v2",$t],
    ["SET","learning:status",$s],
    ["SET","learning:status_json",$j]
  ]' | curl -s -H "$AUTH" -H 'Content-Type: application/json' \
         -X POST "$BASE/pipeline" -d @- >/dev/null
fi

# Verify all
curl -s -H "$AUTH" -X POST "$BASE/pipeline" \
  -H 'Content-Type: application/json' \
  -d '[["GET","xp:bot:senior_total"],["GET","xp:bot:senior_total_v2"],["GET","learning:status"],["GET","learning:status_json"]]' | jq
exit 0
