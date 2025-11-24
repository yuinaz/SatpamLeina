# modules/editor/editor.py

from flask import Blueprint, render_template, request, redirect, flash
from modules.editor.editor_blacklist import load_blacklist, save_blacklist

editor_bp = Blueprint("editor", __name__, template_folder="templates")

@editor_bp.route("/edit-blacklist", methods=["GET", "POST"])
def edit_blacklist():
    if request.method == "POST":
        updated_data = request.form.get("blacklist", "")
        data_list = [line.strip() for line in updated_data.splitlines() if line.strip()]
        save_blacklist(data_list)
        flash("✅ Blacklist berhasil disimpan.", "success")
        return redirect("/edit-blacklist")

    current_blacklist = load_blacklist()
    return render_template("edit_blacklist.html", blacklist="\n".join(current_blacklist))
