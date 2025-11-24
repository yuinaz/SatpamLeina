# modules/discord_bot/routes/editor_blacklist.py
from flask import Blueprint, render_template, request, redirect, url_for, flash

editor_blacklist_bp = Blueprint("editor_blacklist", __name__)

# Halaman edit blacklist sederhana (placeholder)
@editor_blacklist_bp.route("/blacklist", methods=["GET", "POST"])
def edit_blacklist():
    if request.method == "POST":
        # TODO: simpan hash atau kata kunci ke storage/db
        flash("Blacklist updated", "success")
        return redirect(url_for("editor_blacklist.edit_blacklist"))
    return render_template("editor_blacklist.html")

# Endpoint kompatibel lama (jika template lama pakai 'blacklist_image')
@editor_blacklist_bp.route("/blacklist-image", methods=["GET"])
def blacklist_image():
    return redirect(url_for("editor_blacklist.edit_blacklist"))
