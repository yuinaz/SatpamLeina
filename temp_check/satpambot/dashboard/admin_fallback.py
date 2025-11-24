# satpambot/dashboard/admin_fallback.py
import os
from flask import Blueprint, request, session, redirect, url_for, render_template, render_template_string

admin_fallback_bp = Blueprint("admin_fallback", __name__)

def _get_creds():
    user = os.getenv("ADMIN_USERNAME") or os.getenv("SUPER_ADMIN_USER")
    pwd  = os.getenv("ADMIN_PASSWORD") or os.getenv("SUPER_ADMIN_PASS")
    return (user or "").strip(), (pwd or "").strip()

@admin_fallback_bp.route("/admin/login", methods=["GET", "POST"])
@admin_fallback_bp.route("/login", methods=["GET", "POST"])
def admin_login():
    want_user, want_pass = _get_creds()

    # Kalau belum set kredensial admin di ENV, beritahu jelas
    if not want_user or not want_pass:
        return (
            """<html><head><title>Login Admin</title></head>
<body style="background:#0f1320;color:#e6e6e6;font-family:system-ui,Segoe UI,Arial,sans-serif;">
  <div style="max-width:720px;margin:8vh auto;padding:24px;border-radius:16px;background:#161b2e;border:1px solid #28314f">
    <h2 style="margin-top:0">Login Admin tidak aktif</h2>
    <p>Set environment berikut:</p>
    <pre style="background:#0b0f1a;padding:12px;border-radius:10px;white-space:pre-wrap;">ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-strong-password</pre>
    <p>Atau gunakan SUPER_ADMIN_USER / SUPER_ADMIN_PASS.</p>
  </div>
</body></html>""",
            503,
        )

    message = None
    if request.method == "POST":
        u = (request.form.get("username") or "").strip()
        p = (request.form.get("password") or "").strip()
        if u == want_user and p == want_pass:
            session["is_admin"] = True
            session["admin_user"] = u
            return redirect(url_for("admin_fallback.admin_home"))
        message = "Username / password salah."

    # Coba pakai template login.html kalau ada
    try:
        return render_template("login.html", message=message or "")
    except Exception:
        pass  # jatuh ke fallback inline

    # Fallback inline login — gunakan format .format() yang aman (tanpa % / f-string)
    bg = (os.getenv("DASHBOARD_BG_URL") or "").strip()
    logo = (os.getenv("DASHBOARD_LOGO_URL") or "").strip()
    bgstyle = "background-image:url('{0}');background-size:cover;background-position:center;".format(bg) if bg else ""
    logo_tag = '<img class="logo" src="{0}" alt="logo">'.format(logo) if logo else ""
    msg_html = '<div class="err">{0}</div>'.format(message) if message else ""

    html = """<!doctype html><html><head>
<meta charset="utf-8"><title>Login Admin</title>
<style>
  body {{ margin:0; background:#0f1320; color:#e6e6e6; font-family:system-ui,Segoe UI,Arial,sans-serif; {bgstyle} }}
  .card {{ max-width:560px; margin:10vh auto; padding:28px; border-radius:16px; background:#161b2e; border:1px solid #28314f; box-shadow:0 10px 30px rgba(0,0,0,.35) }}
  input,button {{ width:100%; padding:12px 14px; border-radius:10px; border:1px solid #334; outline:none; background:#0b0f1a; color:#e6e6e6; margin-top:10px }}
  button {{ background:#3b82f6; border:0; cursor:pointer }}
  .logo {{ display:block; margin:0 auto 12px auto; max-width:120px; border-radius:12px }}
  .err {{ color:#ff8b8b; margin:8px 0 0 0 }}
</style>
</head><body>
  <div class="card">
    {logo_tag}
    <h2 style="margin-top:0">Login Admin</h2>
    {msg_html}
    <form method="post" autocomplete="off">
      <input name="username" placeholder="Username" required>
      <input type="password" name="password" placeholder="Password" required>
      <button type="submit">Login</button>
    </form>
  </div>
</body></html>""".format(bgstyle=bgstyle, logo_tag=logo_tag, msg_html=msg_html)

    return render_template_string(html)

@admin_fallback_bp.route("/admin/logout", methods=["GET", "POST"])
def admin_logout():
    session.clear()
    return redirect(url_for("admin_fallback.admin_login"))

@admin_fallback_bp.route("/admin")
def admin_home():
    if not session.get("is_admin"):
        return redirect(url_for("admin_fallback.admin_login"))
    # render dashboard utama kalau ada; jika tidak, tampilkan stub sederhana
    try:
        return render_template("dashboard.html")
    except Exception:
        return "<h3>Admin dashboard</h3><p>Login berhasil.</p>", 200
