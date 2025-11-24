from __future__ import annotations
import os, json, time, threading
from typing import Any, Dict, Optional
from pathlib import Path
from urllib import request, error

class FileKV:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {}
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8", errors="ignore") or "{}")
            except Exception:
                self._data = {}

    def _flush(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            v = self._data.get(key)
            return v if isinstance(v, dict) else None

    def set_json(self, key: str, value: Dict[str, Any]) -> None:
        with self._lock:
            self._data[key] = value
            self._flush()

    def setex(self, key: str, seconds: int, value: str = "1") -> None:
        with self._lock:
            now = int(time.time())
            store = self._data.setdefault("__ttl__", {})
            store[key] = {"v": value, "exp": now + int(seconds)}
            self._flush()

    def exists(self, key: str) -> bool:
        with self._lock:
            store = self._data.get("__ttl__", {})
            now = int(time.time())
            if key in store:
                if store[key]["exp"] >= now:
                    return True
                else:
                    del store[key]
                    self._flush()
            return key in self._data

class UpstashREST:
    def __init__(self, rest_url: str, rest_token: str):
        self.url = rest_url.rstrip("/")
        self.token = rest_token

    def _pipeline(self, commands: list[list[str]]) -> list:
        body = json.dumps(commands).encode("utf-8")
        req = request.Request(self.url + "/pipeline", data=body, method="POST")
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Content-Type", "application/json")
        try:
            with request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
                data = json.loads(raw)
                return data
        except error.HTTPError as e:
            raise RuntimeError(f"Upstash HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')}") from e
        except Exception as e:
            raise RuntimeError(f"Upstash request failed: {e}") from e

    @staticmethod
    def _first_result(resp_list: list):
        if not isinstance(resp_list, list) or not resp_list:
            return None
        item = resp_list[0]
        if isinstance(item, dict):
            return item.get("result")
        if isinstance(item, list):
            return item[1] if len(item) > 1 else None
        return None

    def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        res = self._pipeline([["GET", key]])
        val = self._first_result(res)
        if val is None:
            return None
        if isinstance(val, dict):
            return val
        try:
            return json.loads(val)
        except Exception:
            return None

    def set_json(self, key: str, value: Dict[str, Any]) -> None:
        self._pipeline([["SET", key, json.dumps(value, ensure_ascii=False)]])

    def setex(self, key: str, seconds: int, value: str = "1") -> None:
        self._pipeline([["SETEX", key, str(int(seconds)), value]])

    def exists(self, key: str) -> bool:
        res = self._pipeline([["EXISTS", key]])
        val = self._first_result(res)
        try:
            return bool(int(val))
        except Exception:
            return False

def get_kv_for(component: str):
    comp = component.lower()
    choice = (
        os.getenv({"xp":"XP_BACKEND","schedule":"SCHEDULE_BACKEND","dedup":"DEDUP_BACKEND"}[comp] , "")
        or os.getenv("KV_BACKEND", "")
    ).strip().lower() or "file"

    if choice == "upstash_rest":
        url = os.getenv("UPSTASH_REDIS_REST_URL")
        tok = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        if not url or not tok:
            raise RuntimeError(f"{comp} backend upstash_rest requires UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN")
        return UpstashREST(url, tok)

    defaults = {
        "xp": "data/state/xp_store.kv.json",
        "schedule": "data/state/schedules.kv.json",
        "dedup": "data/state/phish_dedup.kv.json",
    }
    envmap = {"xp":"XP_FILE_PATH", "schedule":"SCHEDULE_FILE_PATH", "dedup":"DEDUP_FILE_PATH"}
    path = os.getenv(envmap[comp], defaults[comp])
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return FileKV(path)
