# -*- coding: utf-8 -*-
"""Add-only fallback routes for SatpamBot dashboard.

This module is safe to import multiple times; it only registers routes
that do not already exist in the Flask app.
"""
from __future__ import annotations
from flask import render_template, send_from_directory, Response, redirect
from pathlib import Path

STATIC_DIR = Path(__file__).with_name("static")
TEMPL_DIR  = Path(__file__).with_name("templates")

def _exists(app, rule: str) -> bool:
    try:
        for r in app.url_map.iter_rules():
            if str(r.rule) == rule:
                return True
    except Exception:
        pass
    return False

def register(app):
    # static alias (prevents 404 on assets)
    if "dashboard_static_alias" not in app.view_functions:
        app.add_url_rule(
            "/dashboard-static/<path:filename>",
            "dashboard_static_alias",
            lambda filename: send_from_directory(str(STATIC_DIR), filename, conditional=True),
        )

    # GET /dashboard (render template)
    if not _exists(app, "/dashboard") and "dashboard_index" not in app.view_functions:
        @app.get("/dashboard")
        def dashboard_index():
            try:
                return render_template("dashboard.html")
            except Exception:
                html = (
                    "<!doctype html><meta charset='utf-8'>"
                    "<link rel='stylesheet' href='/dashboard-static/css/neo_aurora_plus.css'>"
                    "<div class='container'><div class='card'><h1>Dashboard</h1>"
                    "<p>Template 'dashboard.html' belum ditemukan.</p></div></div>"
                )
                return Response(html, mimetype="text/html; charset=utf-8")

    # GET /dashboard/ -> redirect ke /dashboard
    if not _exists(app, "/dashboard/") and "dashboard_slash" not in app.view_functions:
        @app.get("/dashboard/")
        def dashboard_slash():
            return redirect("/dashboard", code=302)
