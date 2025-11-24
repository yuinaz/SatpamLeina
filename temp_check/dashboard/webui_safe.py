
# -*- coding: utf-8 -*-
from __future__ import annotations
from flask import Blueprint, render_template_string, send_from_directory, request, redirect, url_for, jsonify
import os, time

bp = Blueprint("dashboard_safe", __name__, url_prefix="")

LOGIN_HTML = """<!doctype html>
<html lang="id"><head>
<meta charset="utf-8"><title>Login</title>
<link rel="stylesheet" href="/dashboard-static/css/login_exact.css">
</head><body>
<div class="lg-wrap">
  <div class="lg-card">
    <div class="lg-avatar"></div>
    <form method="post" action="/dashboard/login" class="lg-form">
      <div class="lg-row"><span class="lg-ico">👤</span><input name="username" placeholder="Username" required></div>
      <div class="lg-row"><span class="lg-ico">🔒</span><input type="password" name="password" placeholder="Password" required></div>
      <div class="lg-actions">
        <label><input type="checkbox" name="remember"> Remember me</label>
        <a class="lg-forgot" href="#" onclick="return false;">Forgot Password?</a>
      </div>
      <div class="lg-cta"><button class="lg-btn" type="submit">LOGIN</button></div>
      <div class="lg-nav"><a href="/">Kembali</a> <span style="flex:1"></span> <a href="/dashboard">Home</a></div>
    </form>
    <div class="lg-pedestal"></div>
  </div>
</div>
</body></html>"""

DASH_HTML = """<!doctype html>
<html lang="id"><head>
<meta charset="utf-8"><title>Dashboard</title>
<link rel="stylesheet" href="/dashboard-static/css/neo_aurora_plus.css">
</head><body>
<nav class="topbar"><div class="brand">SatpamBot</div>
  <div class="spacer"></div>
  <a href="/dashboard">Dashboard</a>
  <a href="/dashboard/security">Security</a>
  <a href="/dashboard/settings">Settings</a>
</nav>
<section class="container">
  <h1>Dashboard</h1>
  <div id="cards" class="grid">
    <div class="card"><div>Guilds</div><b id="g">0</b></div>
    <div class="card"><div>Members</div><b id="m">0</b></div>
    <div class="card"><div>Online</div><b id="o">0</b></div>
    <div class="card"><div>Channels</div><b id="c">0</b></div>
    <div class="card"><div>Threads</div><b id="t">0</b></div>
    <div class="card"><div>Latency</div><b id="l">0 ms</b></div>
  </div>
  <div class="card"><h3>Status</h3><small>Terakhir update: <span id="ts">-</span></small></div>
  <div class="card"><h3>Activity (60fps)</h3><canvas id="chart" width="900" height="180"></canvas></div>
</section>
<script>
async function tick(){
  try{
    const r = await fetch('/api/live/stats');
    const j = await r.json();
    document.getElementById('g').textContent = j.guilds||0;
    document.getElementById('m').textContent = j.members||0;
    document.getElementById('o').textContent = j.online||0;
    document.getElementById('c').textContent = j.channels||0;
    document.getElementById('t').textContent = j.threads||0;
    document.getElementById('l').textContent = (j.latency_ms||0)+' ms';
    document.getElementById('ts').textContent = new Date((j.updated||0)*1000).toLocaleTimeString();
  }catch(e){}
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);
</script>
</body></html>
"""

@bp.get("/dashboard/login")
def login_get():
    return render_template_string(LOGIN_HTML)

@bp.post("/dashboard/login")
def login_post():
    # redirect agar selalu 303 -> /dashboard
    return redirect("/dashboard", code=303)

@bp.get("/dashboard")
def dashboard():
    return render_template_string(DASH_HTML)

# simple static shim (so CSS 200 saat smoketest)
@bp.get("/dashboard-static/<path:rest>")
def static_files(rest:str):
    # Fallback: serve from current working dir if exists; otherwise small CSS inline.
    try:
        base = os.path.join(os.getcwd(), "satpambot","dashboard","static")
        fp = os.path.join(base, rest)
        if os.path.isfile(fp):
            d, f = os.path.split(fp)
            return send_from_directory(d, f)
    except Exception:
        pass
    if rest.endswith(".css"):
        return "/* fallback css */ .topbar{display:flex;gap:16px;padding:10px;background:#101828;color:#fff}.container{padding:20px}.grid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px}.card{background:#111827aa;padding:16px;border-radius:12px;color:#e5e7eb}", 200, {"Content-Type":"text/css"}
    return "", 404
