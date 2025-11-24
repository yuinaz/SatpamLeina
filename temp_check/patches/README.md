This fix pack adds:
- Quiet LLM bootstrap with Groq→Gemini fallback (`a00_llm_provider_bootstrap_quiet_overlay.py`)
- EmbedScribe.update() awaitable wrapper (`a06_embed_scribe_update_fallback_async_overlay.py`)
- Persona `get_active_persona()` fallback (`a00_persona_getter_fallback_overlay.py`)
- QnA auto-learn auto-reply embed (`a24_autolearn_qna_autoreply_fix_overlay.py`)
- Provider smoke test without Python/jq (`scripts/smoke_providers.sh`)

Install:
1) Unzip at repo root.
2) Append `requirements.extra.txt` to your requirements on Render (or copy items).
3) Commit, push, /repo pull, then /repo restart.
