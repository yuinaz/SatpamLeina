
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Safe merge for overrides.render-free.json:
- Keep ALL existing keys.
- Update only QnA titles to correct values.
- Deduplicate comma-separated lists (COGS_ALWAYS, *_CHANNEL_IDS, etc).
- Backup .bak once.
Run: python scripts/apply_leina_env_merge.py
"""
import json, pathlib, shutil, re

P = pathlib.Path("data/config/overrides.render-free.json")

def dedupe_csv(s: str) -> str:
    items = [x.strip() for x in (s or "").split(",") if x.strip()]
    seen, out = set(), []
    for x in items:
        if x not in seen:
            seen.add(x); out.append(x)
    return ",".join(out)

def run():
    if not P.is_file():
        raise SystemExit("overrides.render-free.json not found")
    bak = P.with_suffix(".json.bak")
    if not bak.exists():
        shutil.copy2(P, bak)
        print("[OK] backup created:", bak)
    data = json.loads(P.read_text(encoding="utf-8"))
    env = dict(data.get("env", {}))

    # === Update only the necessary QnA titles ===
    changed = 0
    desired = {
        "QNA_TITLE_ISOLATION": "Question by Leina",
        "QNA_EMBED_TITLE_LEINA": "Question by Leina",
        "QNA_EMBED_TITLE_PROVIDER": "Answer by {provider}",
    }
    for k, v in desired.items():
        if env.get(k) != v:
            env[k] = v; changed += 1

    # Ensure typical required flags exist (do not override existing values)
    env.setdefault("QNA_ENABLE", "1")
    env.setdefault("QNA_AUTOLEARN_ENABLE", "1")
    env.setdefault("QNA_AUTOLEARN_PERIOD_SEC", env.get("QNA_INTERVAL_SEC", "180"))
    env.setdefault("DISABLE_DUPLICATE_QNA", "1")

    # Deduplicate common CSV lists
    for key in list(env.keys()):
        if key.endswith("_CHANNEL_IDS") or key in ("COGS_ALWAYS","COGS_BLOCKLIST","COGS_ALLOWLIST"):
            env[key] = dedupe_csv(env.get(key, ""))

    data["env"] = env
    P.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[DONE] merge complete; keys-updated={changed}")

if __name__ == "__main__":
    run()
