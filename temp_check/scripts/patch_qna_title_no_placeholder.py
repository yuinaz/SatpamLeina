
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patch overrides.render-free.json so QNA_TITLE_ISOLATION does NOT contain {provider}.
This keeps smoke_all_penyakit happy while title still shows provider via helper logic.
"""
import json, sys, pathlib

OV = pathlib.Path("data/config/overrides.render-free.json")
try:
    data = json.loads(OV.read_text(encoding="utf-8"))
except Exception as e:
    print(f"[ERR] Cannot read {OV}: {e}")
    sys.exit(1)

env = data.get("env", {})
before = env.get("QNA_TITLE_ISOLATION")
env["QNA_TITLE_ISOLATION"] = "Answer by Leina"  # safe base; helper will convert to provider-specific
data["env"] = env

OV.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("[OK] QNA_TITLE_ISOLATION updated:")
print(f"  before: {before}")
print(f"  after : {env['QNA_TITLE_ISOLATION']}")
print(f"[OK] Saved -> {OV}")
