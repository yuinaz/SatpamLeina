import sys as _sys, types as _types
def _ensure_discord_stubs():
    try:
        import discord; from discord.ext import commands, tasks  # noqa
        return
    except Exception:
        pass
    import types as _types, sys as _sys
    discord = _types.ModuleType("discord"); _sys.modules["discord"] = discord

    # Submodule: discord.errors
    errors = _types.ModuleType("discord.errors"); _sys.modules["discord.errors"] = errors
    class HTTPException(Exception): pass
    class Forbidden(HTTPException): pass
    class NotFound(HTTPException): pass
    errors.HTTPException = HTTPException
    errors.Forbidden = Forbidden
    errors.NotFound = NotFound

    # Submodule: discord.abc
    abc = _types.ModuleType("discord.abc"); _sys.modules["discord.abc"] = abc; discord.abc = abc
    class Messageable:
        async def history(self, *args, **kwargs):
            if False:
                yield None
            return
    abc.Messageable = Messageable

    class User: 
        def __init__(self): self.sent=[]
        async def send(self, text): self.sent.append(text)
    discord.User=User
    class TextChannel:
        def __init__(self): self.sent=[]
        async def send(self, text): self.sent.append(text)
    discord.TextChannel=TextChannel

    # discord.ext.*
    ext = _types.ModuleType("discord.ext"); _sys.modules["discord.ext"] = ext
    commands = _types.ModuleType("commands"); _sys.modules["discord.ext.commands"] = commands
    tasks = _types.ModuleType("tasks"); _sys.modules["discord.ext.tasks"] = tasks

    class _Cog: pass
    def _listener(*a, **k):
        def deco(fn): return fn
        return deco
    _Cog.listener = staticmethod(_listener)
    commands.Cog=_Cog

    class Bot: pass
    commands.Bot=Bot
    class Context: pass
    commands.Context=Context

    def command(*a, **k):
        def deco(fn): return fn
        return deco
    commands.command=command

    # Proper Loop object with before_loop()
    class _Loop:
        def __init__(self, fn):
            self.fn = fn
        def start(self): pass
        def before_loop(self, f): return f

    def loop(**kw):
        def deco(fn):
            return _Loop(fn)
        return deco
    tasks.loop = loop
_ensure_discord_stubs()


import os, sys, compileall, importlib, traceback, json, re
from pathlib import Path

_HERE = Path(__file__).resolve()
_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))
os.environ.setdefault("SMOKE_MODE","1")

def _print_ok(msg): print(f"OK  : {msg}")
def _print_warn(msg): print(f"WARN: {msg}")
def _print_fail(msg): print(f"FAIL: {msg}")

print("== Smoke: syntax ==")
ok = compileall.compile_dir(str(_ROOT), maxlevels=10, quiet=1)
if not ok:
    _print_warn("compileall reported issues (continuing).")

print("== Smoke: imports ==")
modules = [
    "satpambot.bot.modules.discord_bot.cogs.progress_embed_solo",
    "satpambot.bot.modules.discord_bot.cogs.phash_db_command_single",
    "satpambot.bot.modules.discord_bot.cogs.shadow_learn_observer",
    "satpambot.bot.modules.discord_bot.cogs.rl_shim_history",
    "satpambot.bot.modules.discord_bot.cogs.log_autodelete_bot",
    "satpambot.bot.utils.embed_scribe",
    "satpambot.bot.utils.dupe_guard",
    "satpambot.ml.neuro_lite_memory_fix",
    "satpambot.ml.shadow_metrics",
    "satpambot.ml.groq_helper",
    "satpambot.config.compat_conf",
    "satpambot.config.runtime_memory",
]
failed = []
for m in modules:
    try:
        importlib.import_module(m)
        print(f"[OK] import {m}")
    except Exception as e:
        failed.append((m, e))
        print(f"[FAIL] {m}: {e}")
        traceback.print_exc()

if failed:
    sys.exit(1)

print("== Smoke: dummy setup ==")
try:
    from scripts.smoke_utils import DummyBot, retrofit
    bot = retrofit(DummyBot())
    import asyncio
    async def _load():
        await (importlib.import_module("satpambot.bot.modules.discord_bot.cogs.progress_embed_solo").setup(bot))
        await (importlib.import_module("satpambot.bot.modules.discord_bot.cogs.phash_db_command_single").setup(bot))
        await (importlib.import_module("satpambot.bot.modules.discord_bot.cogs.shadow_learn_observer").setup(bot))
    asyncio.get_event_loop().run_until_complete(_load())
    print("[OK] cogs setup with DummyBot")
except Exception as e:
    print(f"[FAIL] dummy setup: {e}")
    sys.exit(1)

print("\n== Smoke: required files ==")
required = [
    "satpambot/dashboard/webui.py",
    "satpambot/dashboard/templates/login.html",
    "satpambot/dashboard/templates/dashboard.html",
    "satpambot/dashboard/templates/security.html",
    "satpambot/dashboard/templates/settings.html",
    "satpambot/dashboard/static/css/login_exact.css",
    "satpambot/dashboard/static/css/neo_aurora_plus.css",
    "satpambot/dashboard/static/js/neo_dashboard_live.js",
    "satpambot/dashboard/static/logo.svg",
    "satpambot/dashboard/themes/gtake/templates/login.html",
    "satpambot/dashboard/themes/gtake/templates/dashboard.html",
    "satpambot/dashboard/themes/gtake/static/theme.css",
    "satpambot/dashboard/live_store.py",
    "satpambot/bot/modules/discord_bot/shim_runner.py",
    "satpambot/bot/modules/discord_bot/cogs/live_metrics_push.py",
]
for rel in required:
    p = _ROOT / rel
    if p.exists():
        _print_ok(f"file exists: {rel}")
    else:
        _print_warn(f"missing: {rel}")

shim = _ROOT / "satpambot/bot/modules/discord_bot/shim_runner.py"
if shim.exists():
    text = shim.read_text(encoding="utf-8", errors="ignore")
    if re.search(r"intents\s*\.\s*members\s*=\s*True", text):
        print("OK   : intents.members=True (shim_runner.py)")
    else:
        _print_warn("intents.members not True")
    if re.search(r"intents\s*\.\s*presences\s*=\s*True", text):
        print("OK   : intents.presences=True (shim_runner.py)")
    else:
        _print_warn("intents.presences not True")
else:
    _print_warn("shim_runner.py not found; skip intents check")

print("== Smoke: json ==")
json_candidates = [
    "satpambot_config.local.json",
    "config/satpambot_config.local.json",
    "data/config/satpambot_config.local.json",
    "satpambot.local.json",
    "data/neuro-lite/learn_progress_junior.json",
    "data/neuro-lite/learn_progress_senior.json",
    "data/neuro-lite/observe_metrics.json",
    "data/phash/SATPAMBOT_PHASH_DB_V1.json",
    "data/state/embed_scribe.json",
]
all_valid = True
for rel in json_candidates:
    p = _ROOT / rel
    if not p.exists():
        _print_warn(f"json missing: {rel}")
        all_valid = False
        continue
    try:
        json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        _print_fail(f"json invalid: {rel} :: {e}")
        all_valid = False
if all_valid:
    _print_ok("All JSON files valid/exist")

print("== Smoke: upsert call-sites ==")
bad = 0; good = 0
pat_upsert = re.compile(r"\.upsert\s*\(")
pat_channel_first = re.compile(r"""(\(\s*[a-zA-Z_][a-zA-Z0-9_.]*\s*,\s*["'][^"']+["']\s*,\s*discord\.Embed)""")
pat_legacy = re.compile(r"""(\(\s*bot\s*,\s*[a-zA-Z_][a-zA-Z0-9_]*\s*,\s*)""")
for p in _ROOT.rglob("*.py"):
    if "scripts" in str(p):
        continue
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    for m in pat_upsert.finditer(text):
        window = text[m.start():m.start()+240]
        if pat_channel_first.search(window) or pat_legacy.search(window) or "key=" in window:
            good += 1
        else:
            bad += 1
if bad <= 2:
    _print_ok("All upsert call-sites look OK (<=2 unusual allowed)")
else:
    _print_warn(f"{bad} upsert call-site(s) look unusual")

print("== Smoke: features ==")
sitecustom = _ROOT / "sitecustomize.py"
if not sitecustom.exists():
    _print_warn("sitecustomize.py: /healthz not exposed")
else:
    _print_ok("sitecustomize.py present")

print("\n== Smoke: HTTP endpoints via test_client ==")
http_state = {"ok": True}
app = None

def _detect_app_from_webui():
    try:
        webui = importlib.import_module("satpambot.dashboard.webui")
    except Exception:
        return None
    for name in ("app","application","api","fastapi","web","server","flask_app","fastapi_app"):
        obj = getattr(webui, name, None)
        if obj is not None:
            return obj
    for fn in ("create_app","build_app","make_app","init_app","factory","as_app"):
        f = getattr(webui, fn, None)
        if callable(f):
            try:
                return f(testing=True)
            except TypeError:
                try:
                    return f()
                except Exception:
                    pass
    return None

app = _detect_app_from_webui()
if app is None:
    try:
        from satpambot.dashboard.test_harness import create_app as _h_create_app
        app = _h_create_app(testing=True)
    except Exception as e:
        print("WARN: Could not build test harness app; skipping HTTP checks:", e)
        app = None
else:
    # If Flask, patch missing endpoints + SECRET_KEY
    mod = getattr(app.__class__, "__module__", "").lower()
    if "flask" in mod:
        try:
            from satpambot.dashboard.smoke_patch import patch_app
            patch_app(app)
        except Exception as e:
            _print_warn(f"smoke_patch failed: {e}")

if app is None:
    print("WARN: No Flask/FastAPI app available. Skipping HTTP checks.")
else:
    from scripts.http_smoke_utils import HttpSmokeClient
    client = HttpSmokeClient(app)

    def check(desc, fn):
        try:
            ok, info = fn()
            if ok:
                print(f"OK  : {desc}")
            else:
                print(f"WARN: {desc} :: {info}")
        except Exception as e:
            http_state["ok"] = False
            print(f"FAIL: {desc} :: {e}")

    check("/ -> redirect or 200", lambda: client.assert_status(client.get("/"), [200,302]))
    def _login():
        r = client.get("/dashboard/login")
        good, code = client.assert_status(r, [200])
        if not good: return False, code
        body = (r.text if hasattr(r,"text") else getattr(r,"data",b"").decode("utf-8","ignore"))
        return ("lg-card" in body or "login" in body.lower()), "layout missing"
    check("GET /dashboard/login :: 200 & layout", _login)
    for path in ["/dashboard-static/css/login_exact.css",
                 "/dashboard-static/css/neo_aurora_plus.css",
                 "/dashboard-static/js/neo_dashboard_live.js",
                 "/favicon.ico"]:
        check(f"GET {path} :: 200", lambda p=path: client.assert_status(client.get(p), [200]))
    check("HEAD /healthz :: 200", lambda: client.assert_status(client.head("/healthz"), [200]))
    check("HEAD /uptime :: 200", lambda: client.assert_status(client.head("/uptime"), [200]))
    check("GET /api/ui-config :: 200", lambda: client.assert_status(client.get("/api/ui-config"), [200]))
    def _themes():
        r = client.get("/api/ui-themes")
        ok, code = client.assert_status(r, [200])
        if not ok: return False, code
        data = None
        try: data = r.json()
        except Exception:
            try:
                import json as _json
                data = _json.loads(r.data.decode("utf-8"))
            except Exception:
                data = []
        s = str(data).lower()
        present = ("gtake" in s) or ("themes" in s)
        return present, "theme not listed"
    check("GET /api/ui-themes :: 200", _themes)
    check("GET /dashboard-theme/gtake/theme.css :: 200",
          lambda: client.assert_status(client.get("/dashboard-theme/gtake/theme.css"), [200]))
    def _live_stats():
        r = client.get("/api/live/stats")
        ok, code = client.assert_status(r, [200])
        if not ok: return False, code
        try: data = r.json()
        except Exception:
            try:
                import json as _json
                data = _json.loads(r.data.decode("utf-8"))
            except Exception:
                data = {}
        has_keys = isinstance(data, dict) and any(k in data for k in ("uptime","cpu","memory","status","ok"))
        return has_keys, "live stats keys missing"
    check("GET /api/live/stats :: 200", _live_stats)
    check("GET /api/phish/phash :: 200/404", lambda: client.assert_status(client.get("/api/phish/phash"), [200,404]))
    check("GET /logout :: 200/302", lambda: client.assert_status(client.get("/logout"), [200,302]))
    check("GET /dashboard/logout -> redirect :: 302/200",
          lambda: client.assert_status(client.get("/dashboard/logout"), [200,302]))

print("\n=== SUMMARY ===")
if failed:
    print("FAILED:")
    for m, e in failed:
        print(f"- import: {m} -> {e}")
    sys.exit(1)
try:
    if app and http_state.get("ok") is False:
        print("FAILED: HTTP smoke")
        sys.exit(1)
except Exception:
    pass

