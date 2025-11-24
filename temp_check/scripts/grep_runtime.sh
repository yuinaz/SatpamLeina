#!/usr/bin/env bash
set -euo pipefail
LOG=${1:-./your.log}
echo "[XP] signals"
grep -E "xp:|satpam_xp|xp-upstash|xp-award|xp_state" "$LOG" || true
echo
echo "[XP] errors"
grep -E "xp.*(ERROR|Traceback)" "$LOG" || true
echo
echo "[QNA] signals"
grep -E "autolearn|qna|groq|gemini|autoask|autoreply" "$LOG" || true
echo
echo "[QNA] errors"
grep -E "(qna|autolearn).*(ERROR|Traceback)" "$LOG" || true
echo
echo "[CURRICULUM] errors"
grep -E "curriculum_(autoload|tk_sd).*(ERROR|AttributeError)" "$LOG" || true
echo
echo "[EMBED] errors"
grep -E "progress_embed_solo.*(ERROR|AttributeError|NoneType)" "$LOG" || true
