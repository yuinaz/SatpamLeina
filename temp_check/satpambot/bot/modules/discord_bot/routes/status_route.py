# modules/discord_bot/routes/status_route.py
from flask import jsonify, Blueprint

# Blueprint (optional: register via app.register_blueprint)
status_bp = Blueprint("status_bp", __name__)

@status_bp.route("/api/bot_status")
def bot_status_bp():
    return jsonify({"status": "Bot aktif"})

# Back-compat function used by __init__.py to attach into an existing blueprint
def register_status_routes(bp):
    @bp.route("/api/bot_status")
    def bot_status():
        return jsonify({"status": "Bot aktif"})
