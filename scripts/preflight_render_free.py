
# scripts/preflight_render_free.py
import os, sys

def _load_dotenv_light():
    candidates = [
        os.path.join(os.getcwd(), ".env"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env")),
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line=line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k,v = line.split("=",1)
                        k=k.strip(); v=v.strip().strip("'").strip('"')
                        os.environ.setdefault(k, v)
            except Exception as e:
                print(f"WARNING:preflight: failed to read {path}: {e}", file=sys.stderr)

def run():
    _load_dotenv_light()

    # Normalize Discord token envs into DISCORD_TOKEN
    synonyms = [
        "DISCORD_BOT_TOKEN",
        "DISCORD_TOKEN",
        "BOT_TOKEN",
        "discord_bot_token",
        "discord_token",
        "token",
    ]
    val = None
    for name in synonyms:
        v = os.getenv(name)
        if v:
            val = v
            break
    if val and not os.getenv("DISCORD_TOKEN"):
        os.environ["DISCORD_TOKEN"] = val
    if os.getenv("DISCORD_TOKEN") and not os.getenv("DISCORD_BOT_TOKEN"):
        os.environ["DISCORD_BOT_TOKEN"] = os.environ["DISCORD_TOKEN"]

    # Optional alias for Gemini
    if not os.getenv("GEMINI_API_KEY") and os.getenv("GOOGLE_API_KEY"):
        os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY")

    print("INFO:preflight: env aliases applied;",
          "DISCORD_TOKEN?", bool(os.getenv("DISCORD_TOKEN")),
          "GROQ?", bool(os.getenv("GROQ_API_KEY")),
          "GEMINI?", bool(os.getenv("GEMINI_API_KEY")))

if __name__ == "__main__":
    # Allow standalone execution for quick diagnostics
    run()
