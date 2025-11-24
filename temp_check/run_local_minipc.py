from __future__ import annotations

#!/usr/bin/env python3
"""
run_local_minipc.py — single-file runner for local/MINIPC.
- Auto-detects SatpamBot.env (no CLI arg needed).
- Optional: --env PATH to override detection.
- Graceful Ctrl+C / SIGTERM handling (no scary stacktrace).
- Does NOT modify or import anything different from main.py: still calls _entry.main().
"""

import argparse
import os
import signal
import sys
from pathlib import Path
from typing import Optional, Dict

APP_ENV_DEFAULT_NAMES = [
    "SatpamBot.env",     # primary (case-sensitive on POSIX; we also check lowercase)
    "satpambot.env",
    ".env",
]

def _log(msg: str) -> None:
    print(msg, flush=True)

def load_env_file(path: Path, override: bool=False) -> Dict[str, str]:
    """Load KEY=VALUE lines from a simple .env file into os.environ.
    - Ignores blank lines and comments (# ...).
    - Allows quoted values.
    - If override=False (default), existing env vars are preserved.
    Returns the dict of parsed values actually applied to the environment.
    """
    applied: Dict[str, str] = {}
    if not path.exists():
        raise FileNotFoundError(str(path))

    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Support inline comments that are preceded by whitespace
        if " #" in line:
            line = line.split(" #", 1)[0].rstrip()
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip("'").strip('"')

        if override or (key not in os.environ or os.environ.get(key, "") == ""):
            os.environ[key] = val
            applied[key] = val
    return applied

def find_env_file(explicit: Optional[str]=None) -> Optional[Path]:
    """Try to locate the env file with these rules:
    1) explicit path via --env or SATPAMBOT_ENV env var
    2) CWD, script dir, and parents: look for APP_ENV_DEFAULT_NAMES
    3) If multiple candidates exist, prefer the one named 'SatpamBot.env'
    """
    if explicit:
        p = Path(explicit).expanduser().resolve()
        return p if p.exists() else None

    # Also allow environment variable to point to the file
    explicit_env = os.environ.get("SATPAMBOT_ENV", "").strip()
    if explicit_env:
        p = Path(explicit_env).expanduser().resolve()
        if p.exists():
            return p

    search_roots = []
    try:
        search_roots.append(Path.cwd())
    except Exception:
        pass
    try:
        search_roots.append(Path(__file__).parent.resolve())
    except Exception:
        pass

    # Add parents of CWD (up to project root)
    roots = []
    seen = set()
    for root in search_roots:
        for r in [root, *root.parents]:
            if r in seen:
                continue
            roots.append(r)
            seen.add(r)

    candidates = []
    for root in roots:
        for name in APP_ENV_DEFAULT_NAMES:
            p = (root / name)
            if p.exists():
                candidates.append(p.resolve())

    if not candidates:
        return None

    # rank 'SatpamBot.env' highest
    def rank(p: Path) -> int:
        nm = p.name.lower()
        if nm == "satpambot.env":
            return 0
        if nm == ".env":
            return 1
        return 2

    candidates.sort(key=rank)
    return candidates[0]

def _install_signal_handlers():
    """Install simple, friendly signal handlers to avoid noisy tracebacks."""
    def _handler(signum, frame):
        # Keep message short and familiar to your logs
        if signum in (signal.SIGINT,):
            _log("🛑 SIGINT received — shutting down gracefully...")
        elif hasattr(signal, "SIGTERM") and signum == signal.SIGTERM:
            _log("🛑 SIGTERM received — shutting down gracefully...")
        elif hasattr(signal, "SIGBREAK") and signum == signal.SIGBREAK:
            _log("🛑 SIGBREAK received — shutting down gracefully...")
        # Raising SystemExit will unwind cleanly out of main() try/except below
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handler)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _handler)  # Windows console close / Ctrl+Break

def run():
    ap = argparse.ArgumentParser(prog="run_local_minipc", add_help=True)
    ap.add_argument("--env", help="Path to env file (default: auto-detect SatpamBot.env)")
    ap.add_argument("--override", action="store_true", help="Override existing environment variables with values from env file")
    ap.add_argument("--strict", action="store_true", help="Error if env file is missing instead of continuing")
    args = ap.parse_args()

    _install_signal_handlers()

    # Env loading
    env_path = find_env_file(args.env)
    if env_path and env_path.exists():
        applied = load_env_file(env_path, override=args.override)
        _log(f"✅ Loaded env file: {env_path.name}")
    else:
        if args.strict:
            ap.error("Env file not found (looked for SatpamBot.env / .env). Use --env PATH or create SatpamBot.env")
        else:
            _log("ℹ️ No env file found — using system environment")

    # Run legacy entrypoint, unmodified
    try:
        import main as _entry
    except Exception as e:
        _log(f"❌ Failed to import main.py: {e}")
        raise SystemExit(2)

    try:
        _entry.main()
    except SystemExit as e:
        # graceful exits (signals / clean shutdown)
        code = int(getattr(e, "code", 0) or 0)
        _log(f"👋 Exiting cleanly (code={code})")
        raise
    except KeyboardInterrupt:
        _log("👋 Keyboard interrupt — exiting cleanly")
        raise SystemExit(0)
    except Exception as e:
        # unexpected error → fall back to non-zero code
        _log(f"💥 Unhandled error bubbled up from main(): {e}")
        raise SystemExit(1)

if __name__ == "__main__":
    run()
