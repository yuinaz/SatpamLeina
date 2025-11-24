
import json, time, os
from collections import OrderedDict
from pathlib import Path

from satpambot.bot.modules.discord_bot.helpers import hotenv_segment_utils as H

PATH = Path(os.getenv("HOTENV_OVERRIDES_PATH","overrides.render-free.json"))
print(f"[SMOKE] file={PATH} exists={PATH.exists()}")
if not PATH.exists():
    raise SystemExit(1)
data = json.loads(PATH.read_text(encoding="utf-8"), object_pairs_hook=OrderedDict)
env = OrderedDict(data.get("env", {}))
h1 = H.sha1_segments(env)
print("[SMOKE] first hash:", h1)

print("[SMOKE] simulate no-change -> diff should be empty")
a,r,c = H.diff_segments(h1, h1)
print(" added=",a," removed=",r," changed=",c)

# Mutate one key in-memory to simulate change
if env:
    k = next((kk for kk in env.keys() if not kk.startswith('---------------- ')), None)
    if k:
        old = env[k]
        env[k] = str(old) + ""  # noop mutation
        h2 = H.sha1_segments(env)
        a,r,c = H.diff_segments(h1, h2)
        print("[SMOKE] after noop change -> added=",a," removed=",r," changed=",c)
print("SMOKE_OK")
