from _smoke_common import ensure_sys_path, export_env_if_any
import os
ensure_sys_path()
export_env_if_any()
keys = ["GROQ_API_KEY","GOOGLE_API_KEY","GEMINI_API_KEY","DISCORD_BOT_TOKEN","UPSTASH_REDIS_REST_URL","UPSTASH_REDIS_REST_TOKEN"]
print({k: bool(os.getenv(k)) for k in keys})
