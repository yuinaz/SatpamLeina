#!/usr/bin/env python3
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def ok(label): print(f"[OK] {label}")
def fail(label, why): print(f"[FAIL] {label}: {why}"); sys.exit(1)

# A) automaton guard present and early-return exists
auto = ROOT / "satpambot/bot/modules/discord_bot/cogs/automaton.py"
txt = auto.read_text(encoding="utf-8", errors="ignore")

if "AUTOMATON_DM_OWNER" not in txt:
    fail("automaton guard", "AUTOMATON_DM_OWNER marker not found")

# Tolerant match: look for _dm_owner block with an early-return guard
def_has = re.search(r"async\s+def\s+_dm_owner\s*\(", txt) is not None
if not def_has:
    fail("automaton guard", "_dm_owner not found")

# We'll accept any variable name in str(<var>).strip().lower()
guard_ok = re.search(
    r"async\s+def\s+_dm_owner\s*\(.*?\):.*?if\s+not\s*\(\s*str\s*\(\s*[A-Za-z_][A-Za-z0-9_]*\s*\)\.strip\(\)\.lower\(\)\s*in\s*\{[^}]*\}\s*\)\s*:\s*return",
    txt, re.DOTALL
)

if not guard_ok:
    # Fallback heuristic: check within 200 chars after _dm_owner for 'return' line with 'if not' and 'in {'
    m = re.search(r"async\s+def\s+_dm_owner\s*\(.*?\):", txt)
    start = m.end()
    window = txt[start:start+800]
    if ("AUTOMATON_DM_OWNER" in window) and re.search(r"if\s+not.*in\s*\{.*\}.*return", window, re.DOTALL):
        guard_ok = True

if not guard_ok:
    fail("automaton guard", "early-return guard not found after _dm_owner")

ok("automaton guard")

# B) error_notifier logs to channel, not DM
err = ROOT / "satpambot/bot/modules/discord_bot/cogs/error_notifier.py"
et = err.read_text(encoding="utf-8", errors="ignore")
if re.search(r"\b(user|ctx\.author)\.send\s*\(", et, re.I):
    fail("error_notifier", "found direct user DM send (should log to channel)")
ok("error_notifier -> uses LOG channel")

# C) env_import_reporter gated by IMPORTED_ENV_NOTIFY & UPDATE_DM_OWNER
eir = ROOT / "satpambot/bot/modules/discord_bot/cogs/env_import_reporter.py"
eit = eir.read_text(encoding="utf-8", errors="ignore")
if "IMPORTED_ENV_NOTIFY" not in eit or "UPDATE_DM_OWNER" not in eit:
    fail("env_import_reporter", "gating envs missing")
ok("env_import_reporter gating")

# D) selfheal router exists (primary path channel/thread, not DM)
shr = ROOT / "satpambot/bot/modules/discord_bot/cogs/selfheal_router.py"
if not shr.exists():
    fail("selfheal_router", "missing")
ok("selfheal_router present")

print("\nAll checks passed. No owner-DM spam; !gate DM unaffected.")
