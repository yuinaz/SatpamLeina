import os, json

from .ladder_loader import load_ladders, compute_senior_label

class UpstashLite:
    def __init__(self, base, token):
        self.base = (base or "").rstrip("/")
        self.token = token or ""
        self.enabled = bool(self.base and self.token)

    async def get(self, session, key: str):
        if not self.enabled: return None
        import aiohttp
        headers = {"Authorization": f"Bearer {self.token}"}
        async with session.get(f"{self.base}/get/{key}", headers=headers, timeout=15) as r:
            r.raise_for_status()
            j = await r.json()
            return j.get("result")

async def read_learning_status(session, base: str, token: str):
    up = UpstashLite(base, token)
    raw = await up.get(session, "learning:status_json")
    if raw:
        try:
            j = json.loads(raw)
            return {
                "label": j.get("label"),
                "percent": float(j.get("percent") or 0.0),
                "remaining": j.get("remaining"),
                "senior_total": int(j.get("senior_total") or 0),
            }
        except Exception:
            pass
    xp_key = os.getenv("XP_SENIOR_KEY","xp:bot:senior_total")
    total_raw = await up.get(session, xp_key)
    try:
        total = int(total_raw or 0)
    except Exception:
        try:
            jt = json.loads(total_raw); total = int(jt.get("overall",0))
        except Exception: total = 0
    ladders = load_ladders(__file__)
    label, percent, remaining = compute_senior_label(total, ladders)
    return {"label": label, "percent": percent, "remaining": remaining, "senior_total": total}
