# Smoke: QnA LLM & AutoLearn Channel (Env-Hybrid v3)

- Flattens nested JSON in `overrides.render-free.json` and `runtime_env.json`.
- Accepts `GEMINI_API_KEY` **or** `GOOGLE_API_KEY`.
- Channel fallback: `--channel` > `QNA_AUTOLEARN_CHANNEL_ID` > `QNA_CHANNEL_ID` > `QNA_PRIVATE_ID` > `QNA_PUBLIC_ID`.
- Marks LLM available if API key exists; warns if model not set.

## Examples
```bash
python scripts/smoke_qna_autolearn_channel.py --no-channel
python scripts/smoke_qna_autolearn_channel.py --channel 1426571542627614772
```
