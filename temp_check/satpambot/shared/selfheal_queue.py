from __future__ import annotations
import json, time, hashlib
from pathlib import Path
from typing import Dict, Any, List

INBOX = Path("data/selfheal_inbox.jsonl")
QUEUE = Path("data/selfheal_queue")

def ensure_dirs():
    QUEUE.mkdir(parents=True, exist_ok=True)
    INBOX.parent.mkdir(parents=True, exist_ok=True)

def _sig(d: Dict[str, Any]) -> str:
    raw = json.dumps({"msg": d.get("message",""), "where": d.get("where","")}, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]

def enqueue_ticket(payload: Dict[str, Any]) -> Path:
    ensure_dirs()
    sig = _sig(payload)
    ticket = {"id": sig, "created_at": time.time(), "status": "queued", **payload}
    p = QUEUE / f"ticket-{sig}.json"
    p.write_text(json.dumps(ticket, ensure_ascii=False, indent=2), encoding="utf-8")
    return p

def list_tickets() -> List[Dict[str, Any]]:
    ensure_dirs()
    out = []
    for p in sorted(QUEUE.glob("ticket-*.json")):
        try: out.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception: pass
    return out

def update_ticket(ticket_id: str, **fields):
    ensure_dirs()
    p = QUEUE / f"ticket-{ticket_id}.json"
    if not p.exists(): return False
    t = json.loads(p.read_text(encoding="utf-8"))
    t.update(fields)
    p.write_text(json.dumps(t, ensure_ascii=False, indent=2), encoding="utf-8")
    return True
