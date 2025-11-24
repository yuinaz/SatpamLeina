# satpambot/scripts/smoke_test_commands.py
import os, sys, pkgutil, importlib
from types import ModuleType

# pastikan bisa jalan dari mana saja
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

def try_import(modname: str) -> tuple[bool, str]:
    try:
        importlib.import_module(modname)
        return True, ""
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

def main():
    # 1) inti paket bot
    ok, err = try_import("satpambot.bot.modules.discord_bot.discord_bot")
    print(f"[core] discord_bot import: {'OK' if ok else 'FAIL'}{(' | ' + err) if err else ''}")

    # 2) daftar & uji import semua cogs
    try:
        cogs_pkg: ModuleType = importlib.import_module("satpambot.bot.modules.discord_bot.cogs")
        names = [m.name for m in pkgutil.iter_modules(cogs_pkg.__path__) if not m.ispkg]
        print(f"[cogs] found {len(names)} modules")
        fails = []
        for n in sorted(names):
            fq = f"satpambot.bot.modules.discord_bot.cogs.{n}"
            ok, err = try_import(fq)
            if ok:
                print(f"  - {n}: OK")
            else:
                print(f"  - {n}: FAIL | {err}")
                fails.append((n, err))
        if fails:
            print(f"[result] {len(fails)} cog(s) failed import")
        else:
            print("[result] all cogs import OK")
    except Exception as e:
        print(f"[cogs] FAILED to enumerate: {type(e).__name__}: {e}")

if __name__ == "__main__":
    main()
