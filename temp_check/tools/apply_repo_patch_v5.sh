#!/usr/bin/env bash
set -euo pipefail

ZIP="SatpamBot_GH_patch_v5.zip"
PATCH_DIR=".patch_v5"
WFILE="satpambot/dashboard/webui.py"

echo "== SatpamBot Repo Patch v5 (no-rsync, no-unzip) =="

# --- ekstrak ZIP pakai Python ---
if [ ! -f "$ZIP" ]; then
  echo "!! Patch zip '$ZIP' tidak ditemukan. Taruh zip ini di root repo."
  exit 1
fi
rm -rf "$PATCH_DIR"
python - <<'PY'
import zipfile, os, sys
z="SatpamBot_GH_patch_v5.zip"; dst=".patch_v5"
with zipfile.ZipFile(z) as f: f.extractall(dst)
print("extracted to", dst)
PY

# --- copy file2 patch pakai Python (shutil) ---
python - <<'PY'
import os, shutil, pathlib
src = pathlib.Path(".patch_v5")/"satpambot"
dst = pathlib.Path("satpambot")
files = [
  "dashboard/static/css/login_exact.css",
  "dashboard/themes/gtake/templates/login.html",
  "dashboard/templates/security.html",
  "bot/modules/discord_bot/cogs/live_metrics_push.py",
  "bot/modules/discord_bot/cogs/sticky_status.py",
  "dashboard/log_mute_healthz.py",
]
for rel in files:
  s = src / rel
  d = dst / rel
  d.parent.mkdir(parents=True, exist_ok=True)
  shutil.copy2(s, d)
  print("copied", rel)
PY

# --- rapikan sticky legacy (rename bila ada) ---
for f in \
  "satpambot/bot/modules/discord_bot/cogs/status_sticky_patched.py" \
  "satpambot/bot/modules/discord_bot/cogs/sticky_guard.py"
do
  if [ -f "$f" ]; then
    mv -f "$f" "$f.disabled"
    echo "renamed $f -> $f.disabled"
  fi
done

# --- hapus patch login lama kalau ada ---
if git ls-files --error-unmatch login.html.patch >/dev/null 2>&1; then
  git rm -f login.html.patch
  echo "removed tracked login.html.patch"
else
  rm -f login.html.patch 2>/dev/null || true
fi

# --- edit webui.py dengan Python: import mute + route security + metrics proxy ---
python - <<'PY'
from pathlib import Path
p = Path("satpambot/dashboard/webui.py")
txt = p.read_text(encoding="utf-8")
orig = txt

# 1) import mute
imp = "import satpambot.dashboard.log_mute_healthz  # noqa: F401"
if imp not in txt:
    lines = txt.splitlines()
    lines.insert(1, imp)
    txt = "\n".join(lines)

# 2) /security route (pass cfg)
sec_def = '@bp.get("/security")'
if sec_def not in txt:
    txt += """

@bp.get("/security")
def security():
    from flask import current_app, render_template
    cfg = current_app.config.get("UI_CFG") or {}
    return render_template("security.html", title="Security", cfg=cfg)
"""

# 3) /dashboard/api/metrics proxy (opsional untuk tema)
met_def = '@bp.get("/dashboard/api/metrics")'
if met_def not in txt:
    txt += """

@bp.get("/dashboard/api/metrics")
def dashboard_metrics():
    from flask import jsonify
    try:
        from satpambot.dashboard import live_store as _ls
        data = getattr(_ls, "STATS", {}) or {}
        return jsonify(data)
    except Exception:
        return jsonify({"member_count": 0, "online_count": 0, "latency_ms": 0, "cpu": 0.0, "ram": 0.0})
"""

if txt != orig:
    Path(str(p)+".bak").write_text(orig, encoding="utf-8")
    p.write_text(txt, encoding="utf-8")
    print("webui.py updated (+ .bak)")
else:
    print("webui.py unchanged")
PY

# --- tambahkan psutil ke requirements jika belum ---
if [ -f "requirements.txt" ] && ! grep -qi '^psutil' requirements.txt; then
  echo "psutil>=5.9" >> requirements.txt
  echo "added psutil to requirements.txt"
fi

# --- commit ---
git add -A
git commit -m "patch(v5): safe login skin (scoped), sticky anti-spam (WIB, 5m), mute healthz logs, metrics 60s (LeinDiscord), security DnD" || true

echo "== DONE. Restart web + bot. =="
