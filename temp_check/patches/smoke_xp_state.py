import os, asyncio, json, httpx, sys

BASE = os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/")
TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")

async def pipeline(cmds):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    async with httpx.AsyncClient(timeout=30) as cli:
        r = await cli.post(f"{BASE}/pipeline", headers=headers, json=cmds)
        r.raise_for_status()
        return r.json()

async def main():
    cmds = [
        ["GET","xp:store"],
        ["GET","xp:bot:senior_total"],
        ["GET","xp:ladder:TK"],
    ]
    try:
        data = await pipeline(cmds)
        print("[xp-smoke] pipeline OK")
        store = json.loads((data[0] or {}).get("result") or "{}")
        print("  - xp:bot:senior_total:", (data[1] or {}).get("result"))
        print("  - xp:ladder:TK:", (data[2] or {}).get("result"))
    except httpx.HTTPStatusError as e:
        print("HTTP ERROR:", e.response.status_code, e.response.text)

if __name__ == "__main__":
    asyncio.run(main())
