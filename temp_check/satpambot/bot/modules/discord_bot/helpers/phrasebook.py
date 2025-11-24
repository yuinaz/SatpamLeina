import json, os
from typing import Dict, List

_DEFAULT = {
    "slang": [],
    "emoji_map": {},
    "laugh_style": "www",
    "lang_bias": ["id", "en", "jp-romaji", "zh"],
    "tsundere_level": 0.5,
}

class Phrasebook:
    def __init__(self, path: str = "data/phrasebook.json"):
        self.path = path
        self.data = dict(_DEFAULT)
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                self.data.update(json.load(open(self.path, "r", encoding="utf-8")))
            except Exception:
                pass

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        json.dump(self.data, open(self.path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    def add_slang(self, phrase: str) -> None:
        if phrase not in self.data["slang"]:
            self.data["slang"].append(phrase)

    def map_emoji(self, emoji: str, emotion: str) -> None:
        self.data["emoji_map"][emoji] = emotion
