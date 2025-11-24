from __future__ import annotations

from flask import Blueprint, request, jsonify
from .presence_store import get_stats, set_stats

presence_bp = Blueprint("presence", __name__, url_prefix="/api/live")

@presence_bp.get("/stats")
def get_live(): return jsonify(get_stats())

@presence_bp.post("/stats")
def post_live():
    try:
        data = request.get_json(force=True) or {}
    except Exception:
        data = {}
    set_stats(data)
    return jsonify({"ok": True})
