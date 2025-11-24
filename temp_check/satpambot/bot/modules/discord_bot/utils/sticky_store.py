import json, os
from typing import Dict, Any

PATH = os.path.join("data", "sticky_presence.json")

def _load() -> Dict[str, Any]:
    try:
        return json.load(open(PATH, "r", encoding="utf-8"))
    except Exception:
        return {"guilds": {}}

def _save(obj: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    json.dump(obj, open(PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def get_guild(guild_id: int) -> Dict[str, Any]:
    obj = _load()
    return obj["guilds"].get(str(guild_id)) or {}

def upsert_guild(guild_id: int, **fields) -> Dict[str, Any]:
    obj = _load()
    g = obj["guilds"].get(str(guild_id)) or {}
    g.update(fields)
    obj["guilds"][str(guild_id)] = g
    _save(obj)
    return g