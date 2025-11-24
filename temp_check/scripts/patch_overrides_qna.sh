#!/usr/bin/env bash
set -euo pipefail
OVR="data/config/overrides.render-free.json"
BKP="$OVR.bak"
CHID="${PATCH_QNA_CH_ID:-1426571542627614772}"
INTV="${PATCH_QNA_INTERVAL:-180}"

cp "$OVR" "$BKP"
if command -v jq >/dev/null 2>&1; then
  tmp="$(mktemp)"
  jq --arg chid "$CHID" --arg interval "$INTV" '
    .env.QNA_CHANNEL_ID = $chid
    | .env.QNA_INTERVAL_SEC = $interval
  ' "$OVR" > "$tmp"
  mv "$tmp" "$OVR"
  echo "[OK] Patched with jq -> QNA_CHANNEL_ID=$CHID QNA_INTERVAL_SEC=$INTV"
  echo "[OK] Backup at $BKP"
else
  echo "[INFO] jq not found; using Python fallback"
  python scripts/patch_overrides_qna.py
fi
