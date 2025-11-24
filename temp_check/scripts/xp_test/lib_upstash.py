import os, json

class Upstash:
    def __init__(self):
        self.base = os.getenv("UPSTASH_REDIS_REST_URL","").rstrip("/")
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN","")
        self.enabled = bool(self.base and self.token and os.getenv("KV_BACKEND","").lower()=="upstash_rest")

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}", "Content-Type":"application/json"}

    def get(self, key: str):
        if not self.enabled: return None
        import httpx
        with httpx.Client(timeout=15.0) as http:
            r = http.get(f"{self.base}/get/{key}", headers=self._headers())
            r.raise_for_status()
            return r.json().get("result")

    def pipeline(self, commands):
        if not self.enabled: return None
        import httpx
        with httpx.Client(timeout=15.0) as http:
            r = http.post(f"{self.base}/pipeline", headers=self._headers(), json=commands)
            r.raise_for_status()
            try:
                return r.json()
            except Exception:
                return True
