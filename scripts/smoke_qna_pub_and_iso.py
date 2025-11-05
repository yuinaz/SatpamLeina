
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._env_hybrid_loader import export_env
export_env()

print("== QNA PUB & ISO ENV CHECK ==")
need = ["QNA_CHANNEL_ID","QNA_PUBLIC_ID","QNA_PUBLIC_ENABLE","QNA_PROVIDER_ORDER","GROQ_MODEL","GEMINI_MODEL"]
for k in need:
    print(f"{k}={os.getenv(k)}")
print("COGS_ALWAYS contains hotenv_debounce:", "a00_hotenv_debounce_guard_overlay" in (os.getenv("COGS_ALWAYS","")))
print("UPSTASH_URL?", bool(os.getenv("UPSTASH_REDIS_REST_URL")))
print("UPSTASH_TOKEN?", bool(os.getenv("UPSTASH_REDIS_REST_TOKEN")))
print("Hint: Use '!gate unlock' to enable public via Upstash gate if QNA_PUBLIC_ENABLE=0")
