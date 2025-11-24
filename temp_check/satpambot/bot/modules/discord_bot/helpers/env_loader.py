# env_loader (auto)
# Supports .env.local for local testing and .env.prod for production (Render)
import os
from pathlib import Path
from dotenv import load_dotenv

def load_env():
    profile = os.getenv("ENV_PROFILE")  # "local" | "prod" | None
    cwd = Path(".")
    local_file = cwd / ".env.local"
    prod_file = cwd / ".env.prod"

    # Explicit profile
    if profile == "local":
        if local_file.exists():
            load_dotenv(local_file, override=True)   # local should win during dev
        return "local"
    if profile == "prod":
        if prod_file.exists():
            load_dotenv(prod_file, override=False)  # never override Render dashboard
        return "prod"

    # Auto-detect
    if os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID") or os.getenv("RENDER_INSTANCE_ID"):
        if prod_file.exists():
            load_dotenv(prod_file, override=False)  # keep Render dashboard as source of truth
        return "prod"

    # Local default
    if local_file.exists():
        load_dotenv(local_file, override=True)      # local values should apply
        return "local"
    return "none"
