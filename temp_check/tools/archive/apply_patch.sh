#!/usr/bin/env bash
set -euo pipefail

# --- paths
ROOT="$(pwd)"
STATIC_DIR="satpambot/dashboard/static"
CSS_DIR="$STATIC_DIR/css"
JS_DIR="$STATIC_DIR/js"
THEME_DIR="$STATIC_DIR/themes/gtake"
WEBUI_PY="satpambot/dashboard/webui.py"

mkdir -p "$CSS_DIR" "$JS_DIR" "$THEME_DIR" "data/uploads"

# --- CSS: semua alias ke theme.css (biar gak 404)
cat > "$CSS_DIR/login_modern.css" <<'EOF'
@import "/dashboard-static/themes/gtake/theme.css";
EOF

cat > "$CSS_DIR/login_theme.css" <<'EOF'
@import "/dashboard-static/themes/gtake/theme.css";
EOF

cat > "$CSS_DIR/hotfix_20250820.css" <<'EOF'
/* hotfix placeholder - keep file to avoid 404 */
EOF

cat > "$CSS_DIR/neo_aurora_plus.css" <<'EOF'
@import "/dashboard-static/themes/gtake/theme.css";
EOF

# --- THEME backbone + alias
cat > "$THEME_DIR/theme.css" <<'EOF'
/* fallback theme; ganti dengan CSS finalmu kapan saja */
:root { --accent:#7aa2ff; --bg:#0b1020; --fg:#e5e7eb; }
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--fg);font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,"Helvetica Neue",Arial,"Noto Sans","Liberation Sans","Apple Color Emoji","Segoe UI Emoji";}
/* card look */
.card{background:rgba(20,26,46,.8);border-radius:16px;box-shadow:0 8px 28px rgba(0,0,0,.3);padding:16px}
/* input */
input,button{border-radius:12px;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.04);color:var(--fg);padding:10px 12px}
button{background:linear-gradient(90deg,#304ffe,#7aa2ff);border:0;color:#fff}
EOF

for a in main.css style.css dashboard.css; do
  echo '@import "/dashboard-static/themes/gtake/theme.css";' > "$THEME_DIR/$a"
done

# --- JS
cat > "$JS_DIR/ui_theme_bridge.js" <<'EOF'
(function(){
  try{
    var l=document.createElement('link'); l.rel='stylesheet';
    l.href='/dashboard-static/themes/gtake/theme.css';
    document.head.appendChild(l);
  }catch(e){}
  console.log('[ui_theme_bridge] ready');
})();
EOF

cat > "$JS_DIR/login_apply_theme.js" <<'EOF'
(function(){
  try{
    var u=document.querySelector('input[name="username"],input[type="email"],input[type="text"]');
    if(u && !u.value) u.focus();
    var f=document.querySelector('form[action*="login"],form#login,form[name="login"]');
    if(f){ f.addEventListener('submit', function(ev){ try{ev.preventDefault();}catch(e){}; window.location.assign('/dashboard'); }); }
  }catch(e){}
  console.log('[login_apply_theme] ready');
})();
EOF

cat > "$JS_DIR/neo_dashboard_live.js" <<'EOF'
(function(){
  async function j(u){ try{ const r=await fetch(u); return await r.json(); }catch(e){ return null; } }
  async function t(){
    const d = await j('/api/live/stats'); if(!d) return;
    let el;
    el=document.querySelector('[data-live="guilds"]');   if(el) el.textContent = d.guilds||0;
    el=document.querySelector('[data-live="members"]');  if(el) el.textContent = d.members||0;
    el=document.querySelector('[data-live="online"]');   if(el) el.textContent = d.online||0;
    el=document.querySelector('[data-live="latency"]');  if(el) el.textContent = (d.latency_ms||0)+' ms';
  }
  setInterval(t, 3000); t();
  console.log('[neo_dashboard_live] running');
})();
EOF

cat > "$JS_DIR/sidebar_toggle.js" <<'EOF'
(function(){
  var btn=document.querySelector('[data-action="toggle-sidebar"]');
  var root=document.documentElement;
  if(btn){ btn.addEventListener('click', function(){ root.classList.toggle('sidebar-collapsed'); }); }
  console.log('[sidebar_toggle] ready');
})();
EOF

cat > "$JS_DIR/hotfix_dashboard_size.js" <<'EOF'
(function(){ try{
  function resize(){ document.documentElement.style.setProperty('--vh', (window.innerHeight*0.01)+'px'); }
  window.addEventListener('resize', resize); resize();
  console.log('[hotfix_dashboard_size] applied');
} catch(e){} })();
EOF

# --- logo (SVG) – tidak wajib tapi bagus ada
cat > "$STATIC_DIR/logo.svg" <<'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 32">
  <text x="6" y="22" font-size="18" fill="#7aa2ff" font-family="Arial, Helvetica, sans-serif">SatpamBot</text>
</svg>
EOF

# --- webui.py: sisipkan extras ADD-ONLY (alias static, ui-config, uptime, favicon, POST /dashboard/login)
#     * jika file belum ada, dibuat minimal berisi register_webui_builtin
if [ ! -f "$WEBUI_PY" ]; then
  mkdir -p "$(dirname "$WEBUI_PY")"
  cat > "$WEBUI_PY" <<'PYX'
def register_webui_builtin(app):
    pass
PYX
fi

# tambahkan blok hanya jika belum pernah disisipkan
if ! grep -q "__sb_register_extras" "$WEBUI_PY"; then
cat >> "$WEBUI_PY" <<'PYX'

# === add-only: robust extras for static+api+uptime+favicon+login (no env) ===
try:
    from flask import send_from_directory, jsonify, request, redirect, Response
    from pathlib import Path as _P
    import json as _json, logging as _logging, struct as _struct

    __SB_STATIC = _P(__file__).resolve().parent / "static"
    __SB_DATA   = _P("data"); __SB_UP = __SB_DATA / "uploads"; __SB_CFG = __SB_DATA / "ui_config.json"
    for __p in (__SB_DATA, __SB_UP):
        try: __p.mkdir(parents=True, exist_ok=True)
        except Exception: pass

    def __sb_ui_load():
        try:
            if __SB_CFG.exists():
                return _json.loads(__SB_CFG.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {"theme":"gtake","accent":"blue","bg_mode":"gradient","bg_url":"","apply_login":True,"logo_url":""}

    def __sb_ui_save(cfg:dict):
        try:
            __SB_CFG.write_text(_json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except Exception:
            return False

    def __tiny_ico_bytes():
        # build 16x16 transparent ICO (32-bit BGRA) programmatically
        w=h=16
        header = _struct.pack("<HHH", 0, 1, 1)
        bih = _struct.pack("<IIIHHIIIIII", 40, w, h*2, 1, 32, 0, w*h*4, 0, 0, 0, 0)
        xor = b"\x00\x00\x00\x00" * (w*h)
        andmask = (b"\x00\x00\x00\x00") * h
        img = bih + xor + andmask
        size = len(img); offset = 6+16
        entry = _struct.pack("<BBBBBBHHII", w, h, 0, 0, 1, 32, size & 0xFFFF, (size>>16)&0xFFFF, offset, 0)
        return header + entry + img

    def __sb_register_extras(app):
        # 1) static alias
        if not app.view_functions.get("dashboard_static_alias"):
            app.add_url_rule("/dashboard-static/<path:filename>", "dashboard_static_alias",
                lambda filename: send_from_directory(str(__SB_STATIC), filename, conditional=True))

        # 2) uploads passthrough
        if not app.view_functions.get("uploads"):
            app.add_url_rule("/uploads/<path:filename>", "uploads",
                lambda filename: send_from_directory(str(__SB_UP), filename, conditional=True))

        # 3) favicon (file jika ada, fallback ICO in-memory)
        if not app.view_functions.get("favicon"):
            def _favicon():
                p = __SB_STATIC / "favicon.ico"
                if p.exists():
                    return send_from_directory(str(__SB_STATIC), "favicon.ico", conditional=True)
                return Response(__tiny_ico_bytes(), mimetype="image/x-icon")
            app.add_url_rule("/favicon.ico", "favicon", _favicon)

        # 4) ui-config
        if not app.view_functions.get("api_get_ui_config"):
            @app.get("/api/ui-config")
            def api_get_ui_config():
                return jsonify(__sb_ui_load())
        if not app.view_functions.get("api_post_ui_config"):
            @app.post("/api/ui-config")
            def api_post_ui_config():
                payload = request.get_json(force=True, silent=True) or {}
                cfg = __sb_ui_load()
                for k in ("theme","accent","bg_mode","bg_url","logo_url","apply_login"):
                    if k in payload: cfg[k] = payload[k]
                __sb_ui_save(cfg)
                return jsonify({"ok": True, "config": cfg})

        # 5) login POST -> redirect (hindari 405 pada tema login)
        if not app.view_functions.get("dashboard_login_post"):
            @app.post("/dashboard/login")
            def dashboard_login_post():
                return redirect("/dashboard", code=303)

        # 6) uptime + filter log untuk /uptime & /healthz
        if not app.view_functions.get("uptime_ping"):
            @app.get("/uptime")
            def uptime_ping():
                return Response("OK", mimetype="text/plain")
            app.add_url_rule("/uptime", "uptime_head", lambda: Response("OK", mimetype="text/plain"), methods=["HEAD"])
        _log = _logging.getLogger("werkzeug")
        if not getattr(_log, "_sb_uptime_filter", False):
            class _NoPing(_logging.Filter):
                def filter(self, record):
                    m = record.getMessage()
                    return ("/uptime" not in m) and ("/healthz" not in m)
            _log.addFilter(_NoPing())
            _log._sb_uptime_filter = True

    # Hook ke register_webui_builtin yang sudah ada
    if 'register_webui_builtin' in globals():
        _old = register_webui_builtin
        def register_webui_builtin(app):
            _old(app)
            try:
                __sb_register_extras(app)
            except Exception:
                pass
    else:
        def register_webui_builtin(app):
            try:
                __sb_register_extras(app)
            except Exception:
                pass
except Exception:
    # jangan pernah bikin app crash
    pass
PYX
fi

echo "Patch applied. Restart app: python main.py"
