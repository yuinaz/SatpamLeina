from flask import Blueprint, render_template, request, flash, redirect
import os
from .helpers.file_tools import read_file, write_file

editor_bp = Blueprint("editor", __name__)

@editor_bp.route('/editor/blacklist', methods=["GET", "POST"])
def edit_blacklist():
    path = "data/blacklist_image_hashes.txt"
    if request.method == "POST":
        new_data = request.form.get("blacklist_data", "")
        write_file(path, new_data)
        flash("✅ Blacklist berhasil disimpan.", "success")
        return redirect("/editor/blacklist")

    content = read_file(path)
    return render_template("editor_blacklist.html", content=content)
