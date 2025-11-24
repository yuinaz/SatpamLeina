import os, json, aiohttp

class UpstashRedisClient:
    def __init__(self):
        self.base = os.getenv("UPSTASH_REDIS_REST_URL","").rstrip("/")
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN","")
        self.enabled = bool(self.base and self.token)

    async def _req_json(self, method: str, path: str, json_body=None):
        if not self.enabled: return None
        headers = {"Authorization": f"Bearer {self.token}"}
        if method == "POST": headers["Content-Type"] = "application/json"
        try:
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(f"{self.base}{path}", headers=headers, timeout=15) as r:
                        r.raise_for_status()
                        try: return await r.json()
                        except Exception: return None
                else:
                    async with session.post(f"{self.base}{path}", headers=headers, json=json_body, timeout=15) as r:
                        r.raise_for_status()
                        try: return await r.json()
                        except Exception: return True
        except Exception:
            return None

    async def get_raw(self, key: str):
        data = await self._req_json("GET", f"/get/{key}")
        if not data: return None
        return data.get("result")

    async def get_json(self, key: str):
        raw = await self.get_raw(key)
        if raw is None: return None
        try: return json.loads(raw)
        except Exception: return None

    async def pipeline(self, commands):
        return await self._req_json("POST", "/pipeline", json_body=commands)
