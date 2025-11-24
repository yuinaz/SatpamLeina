
import os, json, datetime, pathlib

class BansStore:
    def __init__(self, prefer_path: str | None = None):
        self.candidates = []
        if prefer_path:
            self.candidates.append(str(prefer_path))
        self.candidates += [
            "data/bans.json",
            "satpambot/data/bans.json",
            str(pathlib.Path(__file__).resolve().parents[2] / "data" / "bans.json"),
        ]
    def _read_json(self, p: str):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("items"), list):
                data = data["items"]
            return data if isinstance(data, list) else []
        except Exception:
            return []
    def list_bans(self, limit: int = 50):
        items = []
        for p in self.candidates:
            if p and os.path.exists(p):
                items = self._read_json(p)
                if items:
                    break
        def _k(x):
            v = x.get("created_at")
            try:
                return datetime.datetime.fromisoformat(v.replace("Z","+00:00")) if isinstance(v, str) else datetime.datetime.min
            except Exception:
                return datetime.datetime.min
        items.sort(key=_k, reverse=True)
        return items[:max(1, min(500, int(limit))) if isinstance(limit, int) else 50]
