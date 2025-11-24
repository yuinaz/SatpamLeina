set -euo pipefail

branch="fix/ui-dashboard-routes-templates-$(date +%Y%m%d-%H%M)"
echo "[i] create branch: $branch"
git switch -c "$branch"

ROOT="satpambot/dashboard"
APP="$ROOT/app.py"

mkdir -p "$ROOT/templates/partials" "$ROOT/static/js" "$ROOT/static/css"

mkfile() {
  # mkfile <path> <<'EOF' ... EOF
  local path="$1"
  shift || true
  if [ -f "$path" ]; then
    echo "[-] skip (exists): $path"
  else
    cat > "$path"
    echo "[+] created: $path"
  fi
}

# ---- Templates (buat jika belum ada) ----
mkfile "$ROOT/templates/base.html" <<'EOF'
<!doctype html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{% block title %}SatpamBot{% endblock %}</title>
<link rel="stylesheet" href="{{ url_for('static', filename='css/auth.css') }}?v={{ cache_bust|default('1') }}">
</head><body>
{% block content %}{% endblock %}
{% block extra_scripts %}{% endblock %}
</body></html>
EOF

mkfile "$ROOT/templates/login.html" <<'EOF'
{% extends 'base.html' %}
{% block title %}Masuk Dashboard - SatpamBot{% endblock %}
{% block content %}
<canvas id="particle-canvas" style="position:fixed;inset:0;z-index:0"></canvas>
<div class="login-card" style="position:relative;z-index:1;max-width:560px;margin:10vh auto;padding:16px;background:#151821;border-radius:16px;">
  <h2 style="text-align:center">Masuk Dashboard</h2>
  {% if error %}<div style="color:#ff6b81;margin:8px 0;">{{ error }}</div>{% endif %}
  <form method="post">
    <div style="margin:8px 0"><label>Username</label><input name="user" required style="width:100%"></div>
    <div style="margin:8px 0"><label>Password</label><input type="password" name="pass" required style="width:100%"></div>
    <button style="width:100%;margin-top:10px;">Login</button>
  </form>
</div>
{% endblock %}
{% block extra_scripts %}
<script src="{{ url_for('static', filename='js/particles.min.js') }}"></script>
<script>
(function(){const id='particle-canvas';const c=document.getElementById(id);if(!c||!window.particlesJS)return;
particlesJS(id,{particles:{number:{value:60},color:{value:'#9aa4b2'},size:{value:2},line_linked:{enable:true,distance:140,color:'#9aa4b2',opacity:0.5,width:1}},interactivity:{events:{onhover:{enable:true,mode:'repulse'}}}});
})();
</script>
{% endblock %}
EOF

mkfile "$ROOT/templates/partials/logout_nav.html" <<'EOF'
<div style="position:sticky;top:0;z-index:50;background:rgba(10,11,15,.65);backdrop-filter:blur(8px);padding:8px 12px;margin:-16px -16px 16px -16px;display:flex;gap:8px;align-items:center;justify-content:flex-end;">
  <a href="{{ url_for('__root_dashboard') }}" class="btn" style="text-decoration:none;padding:8px 12px;border-radius:10px;background:#1f2937;color:#e5e7eb">Dashboard</a>
  <a href="{{ url_for('settings_page') }}" class="btn" style="text-decoration:none;padding:8px 12px;border-radius:10px;background:#1f2937;color:#e5e7eb">Settings</a>
  <a href="{{ url_for('servers_page') }}" class="btn" style="text-decoration:none;padding:8px 12px;border-radius:10px;background:#1f2937;color:#e5e7eb">Servers</a>
  <a href="{{ url_for('logout') }}" class="btn" style="text-decoration:none;padding:8px 12px;border-radius:10px;background:#ef4444;color:#fff">Logout</a>
</div>
EOF

mkfile "$ROOT/templates/dashboard.html" <<'EOF'
{% extends 'base.html' %}
{% block title %}Dashboard - SatpamBot{% endblock %}
{% block content %}
{% include 'partials/logout_nav.html' %}
<div class="container">
  <h1>Dashboard</h1>
  <div class="cards">
    <div class="card"><div class="kpi" id="kpi-online">—</div><div class="label">Online</div></div>
    <div class="card"><div class="kpi" id="kpi-msg">—</div><div class="label">Messages Today</div></div>
    <div class="card"><div class="kpi" id="kpi-warn">—</div><div class="label">Warnings</div></div>
    <div class="card"><div class="kpi" id="kpi-uptime">—</div><div class="label">Uptime</div></div>
  </div>
  <canvas id="trafficChart" height="120"></canvas>
  <div id="mini-monitor" class="mini-monitor">CPU: —% | RAM: —MB | Uptime: —</div>
</div>
{% endblock %}
{% block extra_scripts %}
<script src="{{ url_for('static', filename='js/dashboard.js') }}"></script>
<script src="{{ url_for('static', filename='js/mini_monitor.js') }}"></script>
{% endblock %}
EOF

mkfile "$ROOT/templates/settings.html" <<'EOF'
{% extends 'base.html' %}
{% block title %}Settings - SatpamBot{% endblock %}
{% block content %}
{% include 'partials/logout_nav.html' %}
<div class="container">
  <h2>Settings</h2>
  <div class="card"><p>Pengaturan dasar dashboard. (Silakan sesuaikan.)</p></div>
</div>
{% endblock %}
EOF

mkfile "$ROOT/templates/servers.html" <<'EOF'
{% extends 'base.html' %}
{% block title %}Servers - SatpamBot{% endblock %}
{% block content %}
{% include 'partials/logout_nav.html' %}
<div class="container">
  <h2>Servers</h2>
  <div class="card"><p>Daftar server/guild di sini.</p></div>
</div>
{% endblock %}
EOF

# ---- Static (placeholder jika belum ada) ----
mkfile "$ROOT/static/js/particles.min.js" <<'EOF'
// placeholder particles (login pakai CDN juga)
EOF
mkfile "$ROOT/static/js/dashboard.js" <<'EOF'
console.log('dashboard.js loaded');
EOF
mkfile "$ROOT/static/js/mini_monitor.js" <<'EOF'
console.log('mini_monitor.js loaded');
EOF

# ---- Patch app.py: loader ganda + guard + routes ----
if ! grep -q "__login_loop_guard" "$APP"; then
  cat >> "$APP" <<'PY'
# === PATCH START: dashboard templates/routing ===
import os
from jinja2 import ChoiceLoader, FileSystemLoader
from functools import wraps

# Dual template loader (package + root)
try:
    pkg_templates = os.path.join(os.path.dirname(__file__), "templates")
    root_templates = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "templates"))
    loaders = []
    if os.path.isdir(pkg_templates):
        loaders.append(FileSystemLoader(pkg_templates))
    if os.path.isdir(root_templates):
        loaders.append(FileSystemLoader(root_templates))
    if loaders:
        app.jinja_loader = ChoiceLoader(loaders)
except Exception:
    pass

# login_required (ringan) bila belum ada
try:
    login_required
except NameError:
    def login_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not (session.get("admin") or session.get("oauth") or session.get("discord_user")):
                return redirect(url_for("login", next=request.url))
            return fn(*args, **kwargs)
        return wrapper

# Hindari loop redirect pada /login
@app.before_request
def __login_loop_guard():
    p = request.path or "/"
    if p in ("/login", "/admin/login"):
        return None

# Alias /dashboard
@app.get("/dashboard")
@login_required
def dashboard_alias():
    return render_template("dashboard.html")

# Halaman settings & servers
@app.get("/settings")
@login_required
def settings_page():
    return render_template("settings.html")

@app.get("/servers")
@login_required
def servers_page():
    return render_template("servers.html")

# Liveness sederhana untuk front-end
@app.get("/api/live")
def __api_live_fallback():
    from flask import jsonify
    live = str(os.getenv("RUN_BOT","0")).lower() not in ("0","false")
    return jsonify(ok=True, live=bool(live))

# Debug: lihat search paths & keberadaan file
@app.get("/__debug/templates")
def __debug_templates():
    from flask import jsonify
    paths = []
    try:
        loader = app.jinja_loader
        loaders = getattr(loader, "loaders", [loader])
        for L in loaders:
            sp = getattr(L, "searchpath", None)
            if isinstance(sp, (list,tuple)):
                paths.extend(list(sp))
            elif isinstance(sp, str):
                paths.append(sp)
    except Exception:
        pass
    names = ["base.html","login.html","dashboard.html","settings.html","servers.html"]
    found = {}
    for base in paths:
        for n in names:
            fp = os.path.join(base, n)
            found[fp] = os.path.exists(fp)
    return jsonify(paths=paths, found=found)
# === PATCH END ===
PY
else
  echo "[-] app.py already patched; skip app patch"
fi

git add "$ROOT/templates" "$ROOT/static" "$APP"
git commit -m "fix(dashboard): ensure templates exist + logout nav; add /settings, /servers, /api/live, /dashboard; dual-path template loader & login loop guard"

# Buat file patch dari commit terakhir
git format-patch -1 HEAD --stdout > satpambot_dashboard_fix.patch

echo
echo "[✓] Done."
echo "[i] Branch: $branch"
echo "[i] Patch file: satpambot_dashboard_fix.patch"
