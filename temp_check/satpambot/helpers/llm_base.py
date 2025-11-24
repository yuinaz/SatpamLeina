import os

def groq_openai_base() -> str:
    base = os.getenv("OPENAI_BASE_URL", "https://api.groq.com").rstrip("/")
    if base.endswith("/openai/v1"):
        return base
    return base + "/openai/v1"
