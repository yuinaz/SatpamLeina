
import os, json, pathlib, psutil

class MetricsStore:
    def __init__(self, prefer_path: str | None = None, ttl_seconds: int = 120):
        self.ttl = int(ttl_seconds)
        self.candidates = []
        if prefer_path:
            self.candidates.append(str(prefer_path))
        self.candidates += [
            os.getenv("METRICS_FILE") or "",
            "data/metrics.json",
            "satpambot/data/metrics.json",
            str(pathlib.Path(__file__).resolve().parents[2] / "data" / "metrics.json"),
        ]

    def _read_json(self, p: str):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def read(self) -> dict:
        path = None
        for cand in self.candidates:
            if cand and os.path.exists(cand):
                path = cand
                break
        data = self._read_json(path) if path else {}
        # Enrich with host stats if missing
        if "cpu" not in data:
            try:
                data["cpu"] = psutil.cpu_percent(interval=None)
            except Exception:
                data["cpu"] = 0.0
        if "ram_mb" not in data:
            try:
                data["ram_mb"] = round(psutil.virtual_memory().used / (1024*1024), 2)
            except Exception:
                data["ram_mb"] = 0.0
        return data
