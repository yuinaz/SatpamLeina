#!/usr/bin/env python3
# Robust smoke: add repo root to sys.path even if run from /scripts
import sys, os
from pathlib import Path
import importlib

here = Path(__file__).resolve()
# Search upwards for a folder that contains 'satpambot' package
root = None
for up in [here.parent, *here.parents]:
    if (up / "satpambot").exists():
        root = up
        break
if root is None:
    # try one level up from /scripts
    cand = here.parent.parent
    if (cand / "satpambot").exists():
        root = cand

if root is None:
    print("[FAIL] repo root not found; make sure this script is inside your repo")
    sys.exit(1)

sys.path.insert(0, str(root))

try:
    mod = importlib.import_module("satpambot.bot.modules.discord_bot.helpers.embed_scribe")
    EmbedScribe = getattr(mod, "EmbedScribe", None)
    assert EmbedScribe is not None, "EmbedScribe class missing"
    assert hasattr(EmbedScribe, "upsert"), "EmbedScribe.upsert missing"
    print("[OK] embed_scribe import and upsert() present")
except Exception as e:
    print("[FAIL] import embed_scribe:", repr(e))
    sys.exit(1)
