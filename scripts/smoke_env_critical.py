
#!/usr/bin/env python3
# Quick smoke: show critical QnA keys + total count to ensure nothing got wiped.
import json, pathlib
p = pathlib.Path("data/config/overrides.render-free.json")
j = json.loads(p.read_text(encoding="utf-8"))
env = j.get("env", {})
print("Total env keys:", len(env))
for k in ["QNA_TITLE_ISOLATION","QNA_EMBED_TITLE_LEINA","QNA_EMBED_TITLE_PROVIDER",
          "QNA_ENABLE","QNA_AUTOLEARN_ENABLE","DISABLE_DUPLICATE_QNA"]:
    print(f"{k}:", env.get(k))
