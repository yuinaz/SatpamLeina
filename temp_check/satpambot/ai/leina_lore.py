from __future__ import annotations
import json, random, pathlib
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

_DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data" / "persona"

@dataclass
class LoreEntry:
    topic: str
    fact: str
    weight: float = 1.0

def _load_json(name: str) -> Dict[str, Any]:
    p = _DATA_DIR / name
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def random_catchphrase() -> Optional[str]:
    data = _load_json("leina_lore.json")
    phrases: List[str] = data.get("catchphrases", [])
    return random.choice(phrases) if phrases else None

def random_mood() -> Optional[str]:
    data = _load_json("leina_lore.json")
    moods: List[str] = data.get("moods", [])
    return random.choice(moods) if moods else None

def apply_glitch(text: str) -> str:
    data = _load_json("leina_lore.json")
    pats = data.get("glitch_patterns", [])
    prob = float((data.get("constraints") or {}).get("apply_glitch_prob", 0.15))
    if not pats: return text
    if random.random() < prob:
        return f"{text} {random.choice(pats)}"
    return text