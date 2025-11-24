
# shadow_metrics_winfix.py
# Monkey patch penyimpanan metrics JSON agar atomic & aman di Windows (fix FileNotFoundError/PermissionError).
import os, json, time, tempfile, logging
from importlib import import_module

log = logging.getLogger(__name__)

try:
    sm = import_module("satpambot.ml.shadow_metrics")
except Exception as e:
    log.warning("[shadow_fix] tidak bisa import shadow_metrics: %r", e)
    sm = None

def _ensure_dir(path):
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def _atomic_save_windows(path, obj, max_retries=6, backoff=0.15):
    """Tulis ke file JSON secara atomic dengan retry kecil untuk Windows."""
    _ensure_dir(path)
    tmp = None
    for i in range(max_retries):
        try:
            # temp di folder yang sama supaya os.replace() atomic
            dir_ = os.path.dirname(os.path.abspath(path)) or "."
            fd, tmp = tempfile.mkstemp(prefix=os.path.basename(path) + ".", suffix=".tmp", dir=dir_)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as w:
                    json.dump(obj, w, ensure_ascii=False, indent=2)
                    w.flush()
                    os.fsync(w.fileno())
                os.replace(tmp, path)
                return True
            finally:
                # Kalau os.replace gagal, pastikan tmp dibersihkan
                if os.path.exists(tmp):
                    try:
                        os.unlink(tmp)
                    except Exception:
                        pass
        except PermissionError as pe:
            # File diakses proses lain; tunggu sebentar
            time.sleep(backoff * (i + 1))
        except FileNotFoundError:
            _ensure_dir(path)
            time.sleep(backoff * (i + 1))
        except Exception as e:
            log.warning("[shadow_fix] save error: %r", e)
            time.sleep(backoff * (i + 1))
    return False

if sm is not None:
    # Patch fungsi internal _save() jika ada
    orig_save = getattr(sm, "_save", None)
    METRIC_PATH = getattr(sm, "METRIC_PATH", "data/neuro-lite/observe_metrics.json")

    def patched_save(obj):
        ok = _atomic_save_windows(METRIC_PATH, obj)
        if not ok:
            log.error("[shadow_fix] gagal menulis metrics ke %s (lihat retry/permission)",
                      METRIC_PATH)
        return ok

    if orig_save is not None:
        try:
            sm._save = patched_save
            log.info("[shadow_fix] shadow_metrics._save() dipatch aman Windows (path=%s)", METRIC_PATH)
        except Exception as e:
            log.warning("[shadow_fix] gagal mempatch _save: %r", e)
    else:
        log.warning("[shadow_fix] shadow_metrics tidak punya _save untuk dipatch")
