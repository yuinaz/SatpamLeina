
import subprocess, sys
from _smoke_common import ensure_sys_path, export_env_if_any

root = ensure_sys_path()
export_env_if_any()

def run(cmd):
    print("$", " ".join(cmd))
    p = subprocess.run(cmd, cwd=str(root))
    return p.returncode

fail = 0
fail += run([sys.executable, "scripts/smoke_qna_fullstack.py"])
fail += run([sys.executable, "scripts/smoke_xp_ladder_local.py"])
fail += run([sys.executable, "scripts/smoke_boot_hotenv.py"])

print("\n== SUMMARY ==")
print("failures:", fail)
sys.exit(0 if fail == 0 else 1)
