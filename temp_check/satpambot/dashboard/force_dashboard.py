# -*- coding: utf-8 -*-
from __future__ import annotations

from flask import Response, redirect, render_template

def install(app):
    # View that renders template (fallback to inline html if template missing)
    def _view():
        try:
            return render_template("dashboard.html")
        except Exception:
            return Response("<!doctype html><h1>Dashboard</h1><p>Template dashboard.html belum ada.</p>",
                            mimetype="text/html; charset=utf-8")
    # /dashboard
    try:
        app.add_url_rule("/dashboard", endpoint="sb_dash_force", view_func=_view, methods=["GET"])
    except Exception:
        pass
    # /dashboard/ -> redirect ke /dashboard
    try:
        app.add_url_rule("/dashboard/", endpoint="sb_dash_force_slash",
                         view_func=lambda: redirect("/dashboard", code=302), methods=["GET"])
    except Exception:
        pass
