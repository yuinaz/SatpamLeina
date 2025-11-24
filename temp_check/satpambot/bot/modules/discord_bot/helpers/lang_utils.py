import re

def detect_lang(text: str) -> str:
    # Very rough heuristic
    if re.search(r"[\u3040-\u30ff\u31f0-\u31ff\u4e00-\u9faf]", text):
        # contains kana/kanji
        if re.search(r"[\u3040-\u30ff]", text):
            return "ja"
        return "zh"
    if re.search(r"\b(the|and|you|is|are)\b", text.lower()):
        return "en"
    return "id"

def kana_to_romaji(text: str) -> str:
    # Minimal stub: leave as-is (you can replace with real transliteration later)
    return text
