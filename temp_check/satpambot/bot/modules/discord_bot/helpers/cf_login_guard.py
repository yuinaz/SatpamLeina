from __future__ import annotations

# satpambot/bot/modules/discord_bot/helpers/cf_login_guard.py
import json, time, random, pathlib, logging, urllib.request, urllib.error, socket, ssl

log = logging.getLogger(__name__)
_STATE_DIRS = ["/data/satpambot_state", "/tmp"]
_STATE_FILE = "cf_login_guard.json"

def _path():
    for d in _STATE_DIRS:
        try:
            p = pathlib.Path(d); p.mkdir(parents=True, exist_ok=True); return p / _STATE_FILE
        except Exception: continue
    return pathlib.Path("/tmp") / _STATE_FILE

def _now(): return time.time()

def load_state():
    try: return json.loads(_path().read_text("utf-8"))
    except Exception: return {}

def save_state(s):
    try: _path().write_text(json.dumps(s, ensure_ascii=False, indent=2))
    except Exception: pass

def suggested_sleep() -> float:
    s = load_state(); return max(0.0, float(s.get("banned_until_ts", 0.0)) - _now())

def mark_429(ray_id: str | None = None, retry_after_hint: float | None = None):
    base = float(retry_after_hint or 0.0)
    # Default to ~12–20 menit with jitter agar aman dari CF 1015
    if base <= 0: base = 900.0  # 15 menit
    window = max(600.0, min(1800.0, base * 1.2)) + random.uniform(20.0, 80.0)
    s = load_state(); s["banned_until_ts"] = _now() + window
    if ray_id: s["last_ray_id"] = ray_id
    save_state(s)
    log.warning("[cf_login_guard] backoff %.1fs (RayID=%s)", window, ray_id or "-")

_last_probe_ts = 0.0
_last_probe_ok = False

def probe_can_login(timeout: float = 4.0) -> bool:
    """Cek cepat apakah blokir CF sudah lepas.
    GET https://discord.com/api/v10/gateway → 200 JSON berarti boleh.
    Kalau HTML berisi 1015/Cloudflare → masih diblok.
    Throttle: minimal 3 detik antar probe.
    """
    global _last_probe_ts, _last_probe_ok
    now = _now()
    if now - _last_probe_ts < 3.0:
        return _last_probe_ok
    _last_probe_ts = now

    url = "https://discord.com/api/v10/gateway"
    req = urllib.request.Request(url, method="GET", headers={
        "User-Agent": "SatpamBotProbe/1.0 (+https://discord.com)",
        "Accept": "application/json, text/*;q=0.2"
    })
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            code = getattr(resp, "status", 200)
            data = resp.read(2048)
            text = data.decode("utf-8", "ignore")
            if code == 200 and ("url" in text or "wss://" in text):
                _last_probe_ok = True
            else:
                # Non-200 atau konten HTML → anggap masih diblok
                _last_probe_ok = False
    except (urllib.error.HTTPError, urllib.error.URLError, socket.timeout, ssl.SSLError) as e:
        # 429/403 atau HTML Cloudflare juga akan jatuh ke sini
        _last_probe_ok = False
    except Exception:
        _last_probe_ok = False

    # Jika probe OK, bersihkan ban supaya suggested_sleep() tidak menghalangi
    if _last_probe_ok:
        s = load_state()
        s["banned_until_ts"] = _now()  # segera kadaluarsa
        save_state(s)
    return _last_probe_ok
