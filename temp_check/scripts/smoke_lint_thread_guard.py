
# -*- coding: utf-8 -*-
"""
scripts/smoke_lint_thread_guard.py  (tuned)
- Format output tetap sama seperti versi kamu sebelumnya.
- Tambahkan WHITELIST agar warning "while True / time.sleep / threading.Thread" yang memang disengaja
  tidak mengotori output smoke.
- Exit code selalu 0 (tujuan smoke: cepat & informatif, bukan gate CI).
"""
import sys, os, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INCLUDE_DIRS = ["satpambot", "scripts"]
EXCLUDE_DIRS = {".git", "__pycache__", "venv", ".venv", "build", "dist"}

# === Tambahkan path relatif di sini untuk menonaktifkan warning pada file tertentu ===
WHITELIST = {
    # Core bot runner & watchers (loop memang panjang tapi aman)
    "satpambot/bot/modules/discord_bot/discord_bot.py",
    "satpambot/bot/modules/discord_bot/cogs/a00_config_hotreload_overlay.py",
    "satpambot/bot/modules/discord_bot/cogs/a06_prompt_templates_overlay.py",
    "satpambot/bot/modules/discord_bot/cogs/auto_repo_watcher.py",
    "satpambot/bot/modules/discord_bot/cogs/http_429_backoff.py",
    "satpambot/bot/modules/discord_bot/cogs/live_config_watcher.py",
    "satpambot/bot/modules/discord_bot/cogs/rate_limit_guard.py",
    "satpambot/bot/modules/discord_bot/helpers/metrics_agg.py",
    "satpambot/bot/modules/discord_bot/helpers/send_queue.py",
    # Persona & helpers yang memang memakai thread/sleep by design
    "satpambot/bot/persona/loader.py",
    "satpambot/helpers/web_safe_start.py",
    "satpambot/ml/shadow_metrics.py",
    "satpambot/patches/shadow_metrics_winfix.py",
    "satpambot/tools/windows_notifier.py",
    # Scripts util yang bukan bagian runtime event loop
    "scripts/fix_dup_routes.py",
    "scripts/render_entry.py",
    "scripts/self_restart.py",
    # Linter file sendiri
    "scripts/smoke_lint_thread_guard.py",
}

# Tambahan whitelist by-pattern (regex path). Bisa dipakai jika nama file bervariasi:
WHITELIST_PATTERNS = [
    r".*/shadow_metrics.*\.py$",
    r".*/windows_notifier\.py$",
]

def _is_whitelisted(rel):
    if rel in WHITELIST:
        return True
    for pat in WHITELIST_PATTERNS:
        if re.search(pat, rel):
            return True
    return False

def iter_py_files():
    for base in INCLUDE_DIRS:
        p = os.path.join(ROOT, base)
        if not os.path.isdir(p):
            continue
        for dp, dn, fn in os.walk(p):
            dn[:] = [d for d in dn if d not in EXCLUDE_DIRS]
            for f in fn:
                if f.endswith(".py"):
                    rel = os.path.relpath(os.path.join(dp, f), ROOT).replace("\\", "/")
                    yield rel

def check_file(rel):
    if _is_whitelisted(rel):
        return []
    path = os.path.join(ROOT, rel)
    try:
        txt = open(path, "r", encoding="utf-8", errors="ignore").read()
    except Exception:
        return []
    issues = []
    if "threading.Thread(" in txt:
        issues.append("threading.Thread() usage")
    if "time.sleep(" in txt:
        issues.append("time.sleep() usage")
    # heuristik while True tanpa await sleep dekatnya
    for m in re.finditer(r"while\s+True\s*:\s*", txt):
        tail = txt[m.end(): m.end()+200]
        if "await asyncio.sleep" not in tail and "time.sleep" not in tail:
            issues.append("while True without nearby sleep")
            break
    return issues

def main():
    print("== thread_guard_lint ==")
    print(f"-> {sys.executable} scripts/smoke_lint_thread_guard.py")
    total = 0
    warns = []
    for rel in iter_py_files():
        total += 1
        issues = check_file(rel)
        if issues:
            warns.append((rel, issues))
    # Tampilkan sebagian kecil jika masih ada (fallback)
    if warns:
        for rel, issues in warns[:20]:
            print(f"WARNING: {rel}: {', '.join(issues)}")
        if len(warns) > 20:
            print(f"... and {len(warns)-20} more warnings")
    print(f"✓ LINT OK: scanned {total} files.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
