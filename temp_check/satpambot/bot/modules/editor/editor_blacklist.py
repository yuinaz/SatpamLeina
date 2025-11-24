# === modules/editor_blacklist.py
import os
from flask import Blueprint, request, render_template, redirect, flash, url_for
from datetime import datetime

editor_blacklist_bp = Blueprint("editor_blacklist", __name__)

BLACKLIST_PATH = "data/blacklist_image_hashes.txt"
BACKUP_DIR = "backup"

# === Pastikan backup dir ada
os.makedirs(BACKUP_DIR, exist_ok=True)

# ✅ Fungsi bantu

def load_blacklist():
    if not os.path.exists(BLACKLIST_PATH):
        return ""
    with open(BLACKLIST_PATH, "r", encoding="utf-8") as f:
        return f.read()

def save_blacklist(content):
    # Backup dulu
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"blacklist_image_hashes_{timestamp}.txt")
    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(content)
    # Simpan utama
    with open(BLACKLIST_PATH, "w", encoding="utf-8") as f:
        f.write(content)

# ✅ Route Editor
@editor_blacklist_bp.route("/admin/blacklist_editor", methods=["GET", "POST"])
def blacklist_editor():
    if request.method == "POST":
        content = request.form.get("content", "")
        save_blacklist(content)
        flash("✅ Berhasil menyimpan blacklist dan membuat backup.")
        return redirect(url_for("editor_blacklist.blacklist_editor"))

    current_content = load_blacklist()
    return render_template("editor_blacklist.html", content=current_content)

# ✅ Optional: endpoint refresh (jika kamu pakai cache)
blacklist_hashes = set()

def load_blacklist_set():
    global blacklist_hashes
    if os.path.exists(BLACKLIST_PATH):
        with open(BLACKLIST_PATH, "r", encoding="utf-8") as f:
            blacklist_hashes = set(line.strip() for line in f if line.strip())

@editor_blacklist_bp.route("/admin/refresh_blacklist")
def refresh_blacklist():
    load_blacklist_set()
    flash("🔄 Blacklist di-reload dari file.")
    return redirect(url_for("editor_blacklist.blacklist_editor"))
