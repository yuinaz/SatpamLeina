#!/usr/bin/env bash
set -euo pipefail
PROMPT="${1:-apa itu cache?}"
GJSON=$(jq -n --arg p "$PROMPT" '{contents:[{parts:[{text:$p}]}]}')
GROQJSON=$(jq -n --arg p "$PROMPT" --arg m "${LLM_GROQ_MODEL:-llama-3.1-8b-instant}" \
  '{"model":$m,"messages":[{"role":"user","content":$p}],"temperature":0.3}')
echo "[SMOKE] prompt: $PROMPT"
KEY="${GEMINI_API_KEY:-${GOOGLE_API_KEY:-}}"
if [ -n "${KEY}" ]; then
  echo "[TRY] Gemini (${LLM_GEMINI_MODEL:-gemini-2.5-flash-lite})…"
  if TXT=$(echo "$GJSON" \
      | curl -sS -X POST -H "Content-Type: application/json" -H "x-goog-api-key: ${KEY}" \
        --data-binary @- \
        "https://generativelanguage.googleapis.com/v1beta/models/${LLM_GEMINI_MODEL:-gemini-2.5-flash-lite}:generateContent" \
      | jq -re '.candidates[0].content.parts[0].text'); then
    echo "[OK] Answer by GEMINI"
    printf '%s\n' "$TXT"; exit 0
  fi
fi
if [ -n "${GROQ_API_KEY:-}" ]; then
  echo "[TRY] Groq (${LLM_GROQ_MODEL:-llama-3.1-8b-instant})…"
  if TXT=$(echo "$GROQJSON" \
      | curl -sS "https://api.groq.com/openai/v1/chat/completions" \
        -H "Authorization: Bearer $GROQ_API_KEY" -H "Content-Type: application/json" \
        --data-binary @- \
      | jq -re '.choices[0].message.content'); then
    echo "[OK] Answer by GROQ"
    printf '%s\n' "$TXT"; exit 0
  fi
fi
echo "[FAIL] Both providers unavailable or returned unexpected payload."
exit 2
