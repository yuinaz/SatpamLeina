import re

class EmotionModel:
    def __init__(self):
        pass

    def update_from_text(self, user_id: int, text: str):
        t = (text or "").lower()
        if re.search(r"\b(terima kasih|makasih|thanks|mantap|keren|bagus|nice|good)\b", t) or any(x in t for x in ["😂","🤣","😊","❤️","✨"]):
            return "happy", 0.8
        if re.search(r"\b(sedih|down|capek|lelah|gagal)\b", t) or any(x in t for x in ["😢","😭","😞"]):
            return "sad", 0.7
        if re.search(r"\b(marah|kesal|jengkel|bt)\b", t) or any(x in t for x in ["😠","💢","😤"]):
            return "angry", 0.7
        return "neutral", 0.3
