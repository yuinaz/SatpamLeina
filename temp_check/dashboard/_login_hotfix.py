
# --- HOTFIX: guarantee /login and aliases exist ---
try:
    from flask import Flask, render_template, redirect, Blueprint, jsonify, request, send_from_directory
except Exception:
    pass

def __ensure_login_aliases__(app):
    rules = set()
    try:
        rules = {str(r.rule) for r in app.url_map.iter_rules()}
    except Exception:
        pass

    if "/login" not in rules:
        @app.get("/login")
        def __login_hotfix__():
            return render_template("login.html")

    if "/" not in rules:
        @app.get("/")
        def __root_hotfix__():
            return redirect("/login")

    if "/dashboard/login" not in rules:
        @app.get("/dashboard/login")
        def __login_alias_hotfix__():
            return redirect("/login")

    if "/settings" not in rules:
        @app.get("/settings")
        def __settings_alias_hotfix__():
            return redirect("/dashboard/settings")

    try:
        app.logger.info("HOTFIX route map: %s", [str(r.rule) for r in app.url_map.iter_rules()])
    except Exception:
        pass
