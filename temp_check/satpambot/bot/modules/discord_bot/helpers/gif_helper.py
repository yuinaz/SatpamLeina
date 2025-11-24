import os

# Simple stub. If TENOR_API_KEY exists, you can expand later.
def tenor_search(topic: str):
    # To keep it offline-safe, return None (no external calls).
    return None

def pick_emoji(topic: str):
    return {"happy":"😊","sad":"😢","angry":"😠"}.get(topic, "💬")
