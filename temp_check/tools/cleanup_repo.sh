#!/usr/bin/env bash
set -euo pipefail

echo "== GitHub Cleanup Mini v2 =="

# 0) Sanity: jalankan dari root repo (harus ada folder satpambot/)
test -d "satpambot" || { echo "!! Jalankan dari root repo (harus ada folder satpambot)"; exit 1; }

# 1) Bersihkan folder staging / artefak patch lokal
rm -rf .patch_v5 .v5opatch .v5patch 2>/dev/null || true

# 2) Nonaktifkan legacy sticky (hindari dobel)
for f in \
  "satpambot/bot/modules/discord_bot/cogs/status_sticky_patched.py" \
  "satpambot/bot/modules/discord_bot/cogs/sticky_guard.py"
do
  if [ -f "$f" ] && [ ! -f "$f.disabled" ]; then
    mv -f "$f" "$f.disabled"
    echo "[rename] $f -> $f.disabled"
  fi
done

# 3) Hapus patch artefak login kalau ada
for f in login.html.patch login.html.rej login.html.orig; do
  if [ -f "$f" ]; then
    rm -f "$f"
    echo "[rm] $f"
  fi
done

# 4) Pastikan .gitignore, .gitattributes, .editorconfig sehat (append jika belum ada)
append_unique () {
  local file="$1" line="$2"
  touch "$file"
  grep -qxF "$line" "$file" || echo "$line" >> "$file"
}

# .gitignore (tambahkan beberapa pola aman)
append_unique ".gitignore" "__pycache__/"
append_unique ".gitignore" "*.py[cod]"
append_unique ".gitignore" ".env"
append_unique ".gitignore" ".env.*"
append_unique ".gitignore" ".patch_v5"
append_unique ".gitignore" "*.bak"
append_unique ".gitignore" "*.tmp"
append_unique ".gitignore" ".DS_Store"

# .gitattributes (normalisasi EOL)
append_unique ".gitattributes" "* text=auto eol=lf"

# .editorconfig (minimal)
if [ ! -f ".editorconfig" ]; then
  cat > .editorconfig <<'EC'
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
indent_style = space
indent_size = 4
trim_trailing_whitespace = true
EC
  echo "[write] .editorconfig"
fi

# 5) Tambahkan workflow CI smoketest jika belum ada
mkdir -p .github/workflows
if [ ! -f ".github/workflows/smoketest.yml" ]; then
  cat > .github/workflows/smoketest.yml <<'YML'
name: smoketest
on:
  push: { branches: [ main ] }
  pull_request: { branches: [ main ] }
jobs:
  smoketest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt || true; fi
          pip install flask psutil
      - name: Compile syntax
        run: python -m compileall -q .
      - name: Run smoketest script if exists
        run: |
          if [ -f scripts/smoketest_all.py ]; then python scripts/smoketest_all.py; else echo "no smoketest_all.py"; fi
YML
  echo "[write] .github/workflows/smoketest.yml"
fi

echo "== Done. Selanjutnya: git add -A && git commit -m 'repo: cleanup mini v2' && git push =="
