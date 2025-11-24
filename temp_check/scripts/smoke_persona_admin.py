#!/usr/bin/env python3
# (see previous cell for full docstring)
import sys
from pathlib import Path

def _ensure_repo_on_sys_path() -> None:
    here = Path(__file__).resolve()
    for parent in [here.parent] + list(here.parents):
        if (parent / "satpambot").is_dir():
            if str(parent) not in sys.path:
                sys.path.insert(0, str(parent))
            return
    fb = here.parent.parent
    if str(fb) not in sys.path:
        sys.path.insert(0, str(fb))

def main() -> int:
    _ensure_repo_on_sys_path()
    try:
        import satpambot.ai.leina_personality as p
        import satpambot.ai.leina_lore as l
        print("[OK] persona modules import")
    except Exception as e:
        print("[FAIL] persona import:", repr(e))
        return 2
    try:
        import satpambot.bot.modules.discord_bot.cogs.a24c_persona_admin_overlay as c
        print("[OK] persona admin cog import")
    except Exception as e:
        print("[FAIL] admin cog import:", repr(e))
        return 3
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
