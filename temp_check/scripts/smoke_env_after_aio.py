
#!/usr/bin/env python3
import json, pathlib
p = pathlib.Path("data/config/overrides.render-free.json")
j = json.loads(p.read_text(encoding="utf-8"))
env = j.get("env", {})
print("ENV total keys:", len(env))
for k in ["QNA_TITLE_ISOLATION","QNA_EMBED_TITLE_PROVIDER","QNA_PROVIDER_ORDER"]:
    print(k, "=", env.get(k))
