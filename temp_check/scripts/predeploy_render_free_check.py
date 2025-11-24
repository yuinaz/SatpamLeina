#!/usr/bin/env python3
import os, sys, re, json, argparse, compileall, importlib
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
# Ensure repo root import works even when running as "python scripts/xxx.py"
if str(ROOT) not in map(str, sys.path):
    sys.path.insert(0, str(ROOT))

CRITICALS = 0
WARNS = 0

def ok(msg): print(f"[OK] {msg}")
def warn(msg): 
    global WARNS; WARNS += 1; print(f"[WARN] {msg}")
def err(msg):
    global CRITICALS; CRITICALS += 1; print(f"[ERROR] {msg}")

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--relaxed", action="store_true", help="Downgrade some errors to warnings")
    return ap.parse_args()

def path(p: str) -> Path: return ROOT / p

def must_exist(paths: List[str]):
    for p in paths:
        fp = path(p)
        if fp.exists(): ok(f"exists: {p}")
        else: err(f"missing: {p}")

def scan_secrets(file: Path, fatal=True):
    if not file.exists():
        warn(f"secret-scan skipped (not found): {file.relative_to(ROOT)}"); return
    s = file.read_text(encoding="utf-8", errors="ignore")
    patt = re.compile(r'(?i)(api[_-]?key|token|secret|bearer|password)\s*[:=]\s*["\']([A-Za-z0-9._-]{16,})["\']')
    hits = []
    for m in patt.finditer(s):
        key, val = m.group(1), m.group(2)
        if "." in val and any(val.endswith(x) for x in (".com",".net",".org",".io",".dev")):
            continue
        hits.append((key, val[:6]+"..."))
    if '"DISCORD_TOKEN"' in s or '"GROQ_API_KEY"' in s or '"GEMINI_API_KEY"' in s:
        hits.append(("env_key_literal", "hardcoded ENV name/value present"))
    if hits: (err if fatal else warn)(f"{file.relative_to(ROOT)}: possible secrets {hits}")
    else: ok(f"secret-scan clean: {file.relative_to(ROOT)}")

def check_json(file: Path, required_keys: List[str] = None):
    if not file.exists():
        warn(f"json missing (ok if unused): {file.relative_to(ROOT)}"); return
    try:
        obj = json.loads(file.read_text(encoding="utf-8"))
        ok(f"json parse ok: {file.relative_to(ROOT)}")
        if required_keys:
            missing = [k for k in required_keys if k not in obj and k not in obj.get("env",{})]
            if missing: warn(f"json missing keys {missing} in {file.relative_to(ROOT)}")
    except Exception as e:
        err(f"json parse FAIL: {file.relative_to(ROOT)}: {e}")

def compile_repo():
    ok("compiling python modules ...")
    res = compileall.compile_dir(str(ROOT), force=True, quiet=1, maxlevels=10)
    if not res: err("compileall reported failures")
    else: ok("compileall OK")

def check_qna_dualmode():
    fp = path("satpambot/bot/modules/discord_bot/cogs/a24_qna_auto_answer_overlay.py")
    if not fp.exists(): err("QnA overlay missing"); return
    s = fp.read_text(encoding="utf-8", errors="ignore")
    required = ["MODE A: isolation channel", "MODE B: public mention", "Answer by Leina", "Answer by "]
    if all(x in s for x in required): ok("QnA dual-mode markers present")
    else: err("QnA overlay lacks dual-mode markers")
    if ("get_groq_answer" in s or "groq_helper" in s) and ("gemini_client" in s): ok("QnA calls Groq & Gemini")
    else: err("QnA missing provider calls (Groq/Gemini)")

def check_clearchat():
    tb = path("satpambot/bot/modules/discord_bot/cogs/clearchat_tbstyle.py")
    pub = path("satpambot/bot/modules/discord_bot/cogs/a08_public_clearchat.py")
    force = path("satpambot/bot/modules/discord_bot/cogs/a08_clearchat_force_overlay.py")
    for fp in [tb, pub, force]:
        if not fp.exists(): warn(f"clearchat file missing: {fp.relative_to(ROOT)}"); continue
        s = fp.read_text(encoding="utf-8", errors="ignore")
        if "default_permissions(manage_messages=True)" in s or "has_permissions(manage_messages=True)" in s: ok(f"gating present: {fp.name}")
        else: err(f"gating MISSING: {fp.name}")
        if "purge(" in s and "check=_skip_pinned" in s: ok(f"skip_pinned enforced: {fp.name}")
        else: err(f"skip_pinned missing: {fp.name}")

def check_xp_overlay():
    wanted = {"SENIOR": False, "MAGANG": False, "KERJA": False, "GOVERNOR": False}
    files = [
        path("satpambot/bot/modules/discord_bot/cogs/xp_chaining_overlay.py"),
        path("satpambot/bot/modules/discord_bot/cogs/a23_auto_graduate_overlay.py"),
        path("satpambot/bot/modules/discord_bot/cogs/a27_phase_transition_overlay.py"),
        path("satpambot/bot/modules/discord_bot/cogs/a25_governor_cfg_overlay.py"),
    ]
    for fp in files:
        if not fp.exists(): continue
        s = fp.read_text(encoding="utf-8", errors="ignore")
        for k in list(wanted.keys()):
            if k in s: wanted[k] = True
    xpo = files[0]
    if xpo.exists():
        xs = xpo.read_text(encoding="utf-8", errors="ignore")
        if "_cand" in xs or "isdigit()" in xs: ok("XP overlay parse guard present")
        else: err("XP overlay parse guard missing")
    else:
        err("xp_chaining_overlay.py missing")
    for k, present in wanted.items():
        if present: ok(f"phase marker present: {k}")
        else: warn(f"phase marker not found: {k} (check related cogs/config)")

def _load_app_from_module(mod):
    app = getattr(mod, "app", None)
    if app is None:
        for name in ("create_app","build_app","get_app"):
            fac = getattr(mod, name, None)
            if callable(fac):
                try:
                    app = fac()
                    break
                except Exception:
                    continue
    return app

def check_endpoints(relaxed: bool):
    tried = []
    modnames = [
        "satpambot.dashboard.webui_app_export",  # our wrapper first
        "satpambot.dashboard.webui",
        "satpambot.dashboard.app",
        "satpambot.dashboard.main",
        "satpambot.dashboard.__init__",
    ]
    for modname in modnames:
        tried.append(modname)  # record attempt even if import fails
        try:
            mod = importlib.import_module(modname)
            app = _load_app_from_module(mod)
            if app is not None:
                client = app.test_client()
                def _chk(path, expected=(200,)):
                    resp = client.get(path)
                    code = getattr(resp, "status_code", None)
                    if code not in expected:
                        err(f"HTTP {path} -> {code}, expected {expected}")
                    else:
                        ok(f"HTTP {path} -> {code}")
                _chk("/", expected=(200,302))
                for p in ["/dashboard/login", "/dashboard/static/css/neo_aurora_plus.css", "/api/ui-config"]:
                    _chk(p, expected=(200,))
                return
        except Exception:
            continue
    msg = f"web app not loadable; tried {tried}. Export app=... or provide create_app()/build_app()/get_app()."
    if relaxed: warn(msg)
    else: err(msg)

def main():
    args = parse_args()
    relaxed = bool(args.relaxed or os.getenv("PREDEPLOY_RELAXED"))
    must_exist([
        "satpambot/dashboard/webui.py",
        "satpambot/bot/modules/discord_bot/shim_runner.py",
        "satpambot/bot/modules/discord_bot/cogs/a24_qna_auto_answer_overlay.py",
        "satpambot/bot/modules/discord_bot/cogs/clearchat_tbstyle.py",
        "satpambot/bot/modules/discord_bot/cogs/xp_chaining_overlay.py",
        "scripts/smoke_xp_chain.py",
    ])
    compile_repo()
    check_qna_dualmode()
    check_clearchat()
    check_xp_overlay()
    check_json(path("satpambot_config.local.json"))
    scan_secrets(path("data/config/overrides.render-free.json"), fatal=True)
    check_endpoints(relaxed=relaxed)

    print(f"\nSUMMARY: {CRITICALS} error(s), {WARNS} warning(s)")
    sys.exit(0 if CRITICALS==0 else 1)

if __name__ == "__main__":
    main()
