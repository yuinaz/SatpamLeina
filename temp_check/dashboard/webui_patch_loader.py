
# === add-only: favicon + POST /dashboard/login handler ===
try:
    from flask import send_from_directory, redirect, request
    from pathlib import Path as _P2
    _STATIC_DIR2 = _P2(__file__).resolve().parent / "static"

    def _augment_webui_extras(app):
        # Serve /favicon.ico if not already present
        if not app.view_functions.get("favicon"):
            app.add_url_rule("/favicon.ico", "favicon",
                lambda: send_from_directory(str(_STATIC_DIR2), "favicon.ico", conditional=True))

        # Accept POST /dashboard/login to avoid 405 (redirect to dashboard)
        if not app.view_functions.get("dashboard_login_post"):
            @app.post("/dashboard/login")
            def dashboard_login_post():
                # keep semantics minimal: just redirect (front-end/theme-only login)
                return redirect("/dashboard", code=303)
except Exception:
    def _augment_webui_extras(app):  # no-op fallback
        return

