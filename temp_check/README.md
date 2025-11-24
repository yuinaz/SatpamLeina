# Autolearn QnA Full Fix (v4)

Patch ini menyatukan **auto-ask** dan **auto-reply** untuk channel QnA dan
menjamin: (1) koneksi Groq/Gemini, (2) no-duplicate, (3) XP award, (4) aman di Render.

## Env yang dipakai
```
QNA_CHANNEL_ID=1426571542627614772
QNA_PROVIDER_ORDER=groq,gemini

# Upstash dedup (opsional namun direkomendasikan)
UPSTASH_REDIS_REST_URL=...
UPSTASH_REDIS_REST_TOKEN=...
QNA_ASK_DEDUP_NS=qna:recent
QNA_ANSWER_DEDUP_NS=qna:answered

# Groq/Gemini direct fallback (jika bot.llm_ask tidak tersedia)
GROQ_API_KEY=...
GROQ_MODEL=llama-3.1-8b-instant
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-1.5-flash
```

## File utama
- `cogs/a24_autolearn_qna_autoreply_fix_overlay.py` (reply; **ditingkatkan**)
- `cogs/a24_autolearn_qna_autoreply.py` (ask; **dikeraskan**)
- `scripts/autolearn_answer_selftest.py` (selftest offline)
