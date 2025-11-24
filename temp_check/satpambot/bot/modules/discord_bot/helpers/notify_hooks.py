from __future__ import annotations


import os, json
from datetime import datetime, timezone
from typing import Dict, Optional
import urllib.request

def _embed(title: str, description: str, color: int, fields: Optional[Dict[str, str]] = None) -> dict:
    e = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if fields:
        e["fields"] = [{"name": k, "value": v, "inline": True} for k, v in fields.items()]
    return e

def notify_webhook(event: str, extra: Optional[Dict[str, str]] = None) -> bool:
    url = os.getenv("ERRORLOG_WEBHOOK_URL", "").strip()
    if not url:
        return False

    mode = os.getenv("MODE", "bot")
    service = os.getenv("RENDER_SERVICE_NAME", "")
    region = os.getenv("RENDER_REGION", "")
    commit = os.getenv("RENDER_GIT_COMMIT", "")[:7]

    fields = {"Mode": mode}
    if service: fields["Service"] = service
    if region: fields["Region"] = region
    if commit: fields["Commit"] = commit
    if extra:
        fields.update({k: str(v) for k, v in extra.items()})

    if event == "startup":
        title = "✅ Bot Started"
        desc = "Proses dimulai & inisialisasi berjalan."
        color = 0x2ecc71
    elif event == "ready":
        title = "🟢 Bot Ready"
        desc = "Bot login & siap menerima event."
        color = 0x57f287
    else:
        title = "🟥 Bot Shutting Down"
        desc = "SIGTERM diterima, proses akan berhenti."
        color = 0xed4245

    payload = {"embeds": [_embed(title, desc, color, fields)]}
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            resp.read()
        return True
    except Exception:
        return False
