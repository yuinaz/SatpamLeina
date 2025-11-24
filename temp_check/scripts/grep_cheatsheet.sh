#!/usr/bin/env bash
set -euo pipefail

echo "[XP] signals (success):"
grep -E "^\[?a08_xp_upstash_exact_keys_overlay|\[xp-state]|\[xp-upstash-sink]|Computed: |Wrote \(pipeline\):|export_xp_state" -n ${1:-/var/log/render.log} || true

echo
echo "[XP] errors (should be empty):"
grep -E "parse JSON failed|NoneType.*get\(|xp.*Traceback|xp.*error" -n ${1:-/var/log/render.log} || true

echo
echo "[QNA] signals (autoask/autoreply):"
grep -E "\[qna-autoask] channel=|Question by Leina|\[qna-autoreply]|\[auto-learn]" -n ${1:-/var/log/render.log} || true

echo
echo "[QNA] errors (should be empty):"
grep -E "qna.*Traceback|autolearn.*error|autolearn.*failed|qna.*failed" -n ${1:-/var/log/render.log} || true

echo
echo "Tip: pass path to your log file if not using default, e.g."
echo "  bash scripts/grep_cheatsheet.sh ./your.log"
