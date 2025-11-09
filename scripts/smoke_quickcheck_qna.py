
#!/usr/bin/env python3
import json, os, pathlib
p = pathlib.Path("data/config/overrides.render-free.json")
j = json.loads(p.read_text(encoding="utf-8"))
env = j.get("env", {})
print("== QNA QUICK SMOKE ==")
print("- QNA titles:", env.get("QNA_EMBED_TITLE_LEINA"), "->", env.get("QNA_EMBED_TITLE_PROVIDER"))
print("- Provider order:", env.get("QNA_PROVIDER_ORDER"))
print("- Channel:", env.get("QNA_CHANNEL_ID"))
print("- Shadow ENABLE:", env.get("SHADOW_ENABLE"))
