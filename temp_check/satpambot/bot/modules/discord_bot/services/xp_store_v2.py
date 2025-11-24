
import os
import json
import time
import threading
from typing import Any, Dict, Optional

DEFAULT_STORE_PATH = os.environ.get("XP_STORE_FILE", "satpambot/bot/data/xp_store.json")
DEFAULT_AWARDED_IDS_PATH = os.environ.get("XP_AWARDED_IDS_FILE", "satpambot/bot/data/xp_awarded_ids.json")

def _ensure_dirs(path: str) -> None:
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def _atomic_write(path: str, data: str, mode: str = "w", encoding: str = "utf-8"):
    _ensure_dirs(path)
    tmp = f"{path}.tmp"
    with open(tmp, mode, encoding=encoding) as f:
        f.write(data)
    os.replace(tmp, path)

class _UpstashReplicator:
    """
    Minimal Upstash Redis REST replicator (optional).
    Enabled when XP_UPSTASH_ENABLED=true and UPSTASH_REDIS_REST_URL & UPSTASH_REDIS_REST_TOKEN are set.
    Endpoint style used: {base}/{cmd}/{key}/{value?} with Authorization: Bearer <token>.
    Safe no-op on any error; local store remains source of truth.
    """
    __slots__ = ("enabled", "base", "token", "timeout")

    def __init__(self):
        self.enabled = str(os.environ.get("XP_UPSTASH_ENABLED", "")).lower() in ("1","true","yes","on")
        self.base = os.environ.get("UPSTASH_REDIS_REST_URL")
        self.token = os.environ.get("UPSTASH_REDIS_REST_TOKEN") or os.environ.get("UPSTASH_TOKEN")
        self.timeout = float(os.environ.get("UPSTASH_TIMEOUT", "5"))
        if not (self.enabled and self.base and self.token):
            self.enabled = False

    def _call(self, path: str, method: str = "POST", allow_get: bool = False):
        if not self.enabled:
            return None
        try:
            import requests
        except Exception:
            return None
        try:
            url = self.base.rstrip("/") + path
            headers = {"Authorization": f"Bearer {self.token}"}
            if method == "POST":
                return requests.post(url, headers=headers, timeout=self.timeout)
            if allow_get and method == "GET":
                return requests.get(url, headers=headers, timeout=self.timeout)
            return None
        except Exception:
            return None

    @staticmethod
    def _q(s: str) -> str:
        from urllib.parse import quote
        return quote(s, safe="")

    def set_json(self, key: str, value: dict):
        if not self.enabled:
            return
        try:
            payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            self._call(f"/set/{self._q(key)}/{self._q(payload)}", "POST")
        except Exception:
            pass

    def set_str(self, key: str, value: str):
        if not self.enabled:
            return
        try:
            self._call(f"/set/{self._q(key)}/{self._q(value)}", "POST")
        except Exception:
            pass

    def incrby(self, key: str, amount: int):
        if not self.enabled:
            return
        try:
            self._call(f"/incrby/{self._q(key)}/{int(amount)}", "POST")
        except Exception:
            pass

class XPStoreV2:
    """
    File-backed XP store (atomic JSON) + optional Upstash replication.
    Structure:
    {
      "version": 2,
      "users": { "<user_id>": {"total": int, "updated_at": ts, "by_reason": {...}} },
      "awards": [{"ts": ts, "user_id": str, "amount": int, "reason": str|None, "ctx": dict}],
      "stats": {"total_awards": int, "total_users": int},
      "updated_at": ts
    }
    """
    def __init__(self, store_path: Optional[str] = None, awarded_ids_path: Optional[str] = None):
        self.store_path = store_path or DEFAULT_STORE_PATH
        self.awarded_ids_path = awarded_ids_path or DEFAULT_AWARDED_IDS_PATH
        self._lock = threading.RLock()
        self._data = self._load_or_init()
        self._awarded_ids = self._load_awarded_ids()
        self._upstash = _UpstashReplicator()

    # ---------- load/save ----------
    def _load_or_init(self) -> Dict[str, Any]:
        if not os.path.exists(self.store_path):
            now = int(time.time())
            d = {"version": 2, "users": {}, "awards": [], "stats": {"total_awards": 0, "total_users": 0}, "updated_at": now}
            _atomic_write(self.store_path, json.dumps(d, ensure_ascii=False, indent=2))
            return d
        try:
            with open(self.store_path, "r", encoding="utf-8") as f:
                d = json.load(f)
            if "version" not in d:
                d["version"] = 2
            if "users" not in d: d["users"] = {}
            if "awards" not in d: d["awards"] = []
            if "stats" not in d: d["stats"] = {}
            if "total_awards" not in d["stats"]: d["stats"]["total_awards"] = len(d.get("awards", []))
            if "total_users" not in d["stats"]: d["stats"]["total_users"] = len(d.get("users", {}))
            if "updated_at" not in d: d["updated_at"] = int(time.time())
            return d
        except Exception:
            # rotate corrupted json
            broken = f"{self.store_path}.broken.{int(time.time())}"
            try:
                os.replace(self.store_path, broken)
            except Exception:
                pass
            return {"version": 2, "users": {}, "awards": [], "stats": {"total_awards": 0, "total_users": 0}, "updated_at": int(time.time())}

    def _load_awarded_ids(self):
        if not os.path.exists(self.awarded_ids_path):
            _atomic_write(self.awarded_ids_path, json.dumps({"ids": []}, ensure_ascii=False, indent=2))
            return set()
        try:
            with open(self.awarded_ids_path, "r", encoding="utf-8") as f:
                d = json.load(f)
            return set(d.get("ids", []))
        except Exception:
            return set()

    def _save_awarded_ids(self):
        try:
            _atomic_write(self.awarded_ids_path, json.dumps({"ids": sorted(self._awarded_ids)}, ensure_ascii=False, indent=2))
        except Exception:
            pass

    def _save(self):
        self._data["stats"]["total_users"] = len(self._data.get("users", {}))
        _atomic_write(self.store_path, json.dumps(self._data, ensure_ascii=False, indent=2))

    # ---------- public API ----------
    def has_awarded(self, award_key: Optional[str]) -> bool:
        if not award_key:
            return False
        with self._lock:
            return award_key in self._awarded_ids

    def mark_awarded(self, award_key: Optional[str]):
        if not award_key:
            return
        with self._lock:
            self._awarded_ids.add(award_key)
            self._save_awarded_ids()

    def get_total(self, user_id: int) -> int:
        with self._lock:
            u = self._data["users"].get(str(user_id))
            return int(u.get("total", 0)) if u else 0

    def add_xp(self, user_id: int, amount: int = 1, reason: Optional[str] = None,
               context: Optional[Dict[str, Any]] = None, award_key: Optional[str] = None) -> int:
        """
        Tambah XP dan kembalikan total baru.
        award_key (mis. message_id) dipakai buat idempotency agar gak dobel.
        """
        now = int(time.time())
        with self._lock:
            if award_key and award_key in self._awarded_ids:
                return self.get_total(user_id)

            users = self._data.setdefault("users", {})
            u = users.setdefault(str(user_id), {"total": 0, "updated_at": now, "by_reason": {}})
            u["total"] = int(u.get("total", 0)) + int(amount)
            u["updated_at"] = now
            if reason:
                u["by_reason"][reason] = int(u["by_reason"].get(reason, 0)) + int(amount)

            self._data.setdefault("awards", []).append({
                "ts": now,
                "user_id": str(user_id),
                "amount": int(amount),
                "reason": reason,
                "ctx": context or {},
            })
            self._data.setdefault("stats", {}).setdefault("total_awards", 0)
            self._data["stats"]["total_awards"] += 1
            self._data["updated_at"] = now

            if award_key:
                self._awarded_ids.add(award_key)

            # persist locally first
            self._save()
            self._save_awarded_ids()

            # best-effort replicate to Upstash
            try:
                if self._upstash.enabled:
                    # total per user
                    self._upstash.set_str(f"xp:total:{user_id}", str(u["total"]))
                    # by_reason counts
                    if reason:
                        self._upstash.incrby(f"xp:by_reason:{user_id}:{reason}", int(amount))
                    # global stats & last updated
                    self._upstash.set_str("xp:stats:total_awards", str(self._data["stats"]["total_awards"]))
                    self._upstash.set_str("xp:stats:total_users", str(self._data["stats"]["total_users"]))
                    self._upstash.set_str("xp:updated_at", str(self._data["updated_at"]))
                    # whole user object (optional)
                    self._upstash.set_json(f"xp:user:{user_id}", u)
            except Exception:
                # never block or raise
                pass

            return u["total"]
