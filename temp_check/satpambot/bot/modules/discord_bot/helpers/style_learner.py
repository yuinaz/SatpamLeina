import re
from collections import defaultdict, deque

class StyleLearner:
    def __init__(self, window: int = 10):
        self.window = window
        self.hist = defaultdict(lambda: deque(maxlen=self.window))

    def observe(self, user_id: int, text: str):
        t = text or ""
        exclam = t.count("!")
        www = len(re.findall(r"\bwww+\b", t.lower()))
        wkwk = len(re.findall(r"\bwk(?:wk)+\b", t.lower()))
        lol = len(re.findall(r"\blol+\b", t.lower()))
        self.hist[user_id].append({"exclam": exclam, "www": www, "wkwk": wkwk, "lol": lol})

    def recent_summary(self, user_id: int):
        arr = list(self.hist[user_id])
        if not arr:
            return {"exclam":0,"www":0,"wkwk":0,"lol":0}
        out = {"exclam":0,"www":0,"wkwk":0,"lol":0}
        for r in arr:
            for k in out.keys(): out[k] += r.get(k,0)
        return out
