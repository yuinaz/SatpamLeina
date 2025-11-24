#!/usr/bin/env python3
# predeploy_check.py

import os, sys, ast, importlib.util, types, asyncio, json
from pathlib import Path

REPO_ROOT = Path.cwd()

LEARN_PATH = REPO_ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "cogs" / "a00_learning_status_refresh_overlay.py"
ADMIN_PATH = REPO_ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "cogs" / "admin.py"

def compile_check(path: Path):
    src = path.read_text(encoding="utf-8", errors="ignore")
    ast.parse(src, filename=str(path))
    print(f"[OK] Syntax: {path}")

def load_module_from_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class FakeResp:
    def __init__(self, payload): self._p = payload
    def json(self): return self._p

class FakeAsyncClient:
    def __init__(self, *a, **kw): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *exc): pass
    async def get(self, url, headers=None):
        # Simulate Upstash GET xp:bot:senior_total
        xp = os.environ.get("TEST_XP_RESULT", "82532")
        return FakeResp({"result": xp})
    async def post(self, url, headers=None, json=None):
        print("[FAKE POST]", url, "payload=", json)
        return FakeResp({"result":"OK"})

async def run_learning_refresh_once():
    # Ensure ladder path exists (create minimal if missing)
    ladder_path = Path(os.getenv("LADDER_PATH", "data/neuro-lite/ladder.json"))
    ladder_path.parent.mkdir(parents=True, exist_ok=True)
    if not ladder_path.exists():
        # minimal ladder for test
        ladder_path.write_text(json.dumps({"senior": {
            "TK": {"L1": 200, "L2": 300},
            "SD": {"L1": 500, "L2": 700},
            "SMP": {"L1": 2000, "L2": 3000},
            "SMA": {"L1": 4200, "L2": 4800},
            "KULIAH-S1": {"L1": 12000},
            "KULIAH-S2": {"L1": 40000}
        }}, indent=2), encoding="utf-8")
    os.environ.setdefault("UPSTASH_REDIS_REST_URL", "https://fake.upstash.local")
    os.environ.setdefault("UPSTASH_REDIS_REST_TOKEN", "fake_token")

    mod = load_module_from_path("learning_overlay", LEARN_PATH)

    # Monkeypatch httpx inside the module
    mod.httpx = types.SimpleNamespace(AsyncClient=FakeAsyncClient)

    # Instantiate and run the internal refresh method directly
    cog = mod.LearningStatusRefresh(bot=None)
    await cog._refresh_once()
    print("[OK] Learning overlay refresh executed without exception.")

def main():
    try:
        compile_check(LEARN_PATH)
        compile_check(ADMIN_PATH)
    except Exception as e:
        print("[FAIL] Syntax check:", e)
        sys.exit(2)

    try:
        asyncio.run(run_learning_refresh_once())
    except Exception as e:
        print("[FAIL] Learning overlay runtime:", repr(e))
        sys.exit(3)

    print("\nAll predeploy checks passed ✅")

if __name__ == "__main__":
    main()
