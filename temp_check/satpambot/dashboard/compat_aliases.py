
def register_compat(app):
    @app.route("/dashboard-static/<path:fname>")
    def _compat_dashboard_static(fname):
        if fname.endswith(".js"):
            return ("console.log('compat ui bridge ok');", 200, {"Content-Type": "application/javascript"})
        if fname.endswith(".css"):
            return ("/* compat css ok */", 200, {"Content-Type": "text/css"})
        if fname.endswith(".svg"):
            return ("", 200, {"Content-Type": "image/svg+xml"})
        return ("", 200, {"Content-Type": "text/plain"})

    @app.route("/dashboard-theme/<theme>/theme.css")
    def _theme_css(theme):
        # Serve packaged theme file if present, otherwise minimal fallback
        try:
            from flask import send_from_directory
            import os
            base = os.path.join(os.path.dirname(__file__), "theme", theme)
            return send_from_directory(base, "theme.css")
        except Exception:
            css = ":root{--bg:#0b1220;--text:#dbe1ff} body{background:var(--bg);color:var(--text);}"
            return (css, 200, {"Content-Type":"text/css"})
    @app.route("/favicon.ico")
    def _favicon():
        import base64
        data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAukB9Xc2lZ0AAAAASUVORK5CYII=")
        return (data, 200, {"Content-Type": "image/png"})
