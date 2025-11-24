# sheets_test.py - send a sample row to Google Sheets webhook
import os, json, asyncio, aiohttp
from datetime import datetime, timezone

URL = os.getenv("SHEETS_WEBHOOK_URL")
TOKEN = os.getenv("SHEETS_TOKEN")

async def main():
    if not URL or not TOKEN:
        print("Missing SHEETS_WEBHOOK_URL or SHEETS_TOKEN in env")
        return
    payload = {
        "token": TOKEN,
        "sheet": "Commands",
        "type": "command",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "guild_id": "local-test",
        "user_id": "0",
        "command": "selftest",
        "status": "ok",
        "duration_ms": 1
    }
    async with aiohttp.ClientSession() as s:
        async with s.post(URL, json=payload) as r:
            print("HTTP", r.status)
            txt = await r.text()
            print(txt)

if __name__ == "__main__":
    asyncio.run(main())
