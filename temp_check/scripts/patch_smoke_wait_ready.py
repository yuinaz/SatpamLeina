#!/usr/bin/env python3
# In-place fixer for scripts/smoke_cogs.py: ensure wait_until_ready() stub exists safely.
import re, sys, pathlib

path = pathlib.Path("scripts/smoke_cogs.py")
src = path.read_text(encoding="utf-8")

# 1) Remove any previous injected block (identified by our marker)
pattern = re.compile(
    r"\n# --- smoke stub: ensure wait_until_ready exists.*?\n# -+\n",
    re.DOTALL
)
src2 = re.sub(pattern, "\n", src)

# 2) Append EOF-safe stub
stub = """
# --- smoke stub: ensure wait_until_ready exists (EOF safe, do not alter config) ---
try:
    _bot = bot  # noqa
except NameError:
    _bot = None
if _bot is not None and not hasattr(_bot, "wait_until_ready"):
    async def _noop_wait():  # pragma: no cover
        return None
    _bot.wait_until_ready = _noop_wait
# -------------------------------------------------------------------------------
"""

if not src2.rstrip().endswith("\n"):
    src2 += "\n"
src2 += stub

path.write_text(src2, encoding="utf-8")
print("[OK] Patched scripts/smoke_cogs.py with EOF-safe wait_until_ready stub.")
