
import os, re, time, sqlite3
from typing import Iterable, Tuple

DB_PATH = os.getenv("NEUROLITE_MEMORY_DB",
    os.path.join(os.path.dirname(__file__), "..","..","..","..","data","memory.sqlite3"))

TOKEN_RE = re.compile(r"[a-z0-9_#]+", re.IGNORECASE)

STOP = {
    "yang","dan","di","ke","dari","aku","kamu","gua","gue","gw","lu","loe",
    "the","and","you","is","are","itu","ini","aja","ajaah","ajaahh",
    "ya","iya","iyaa","lah","lahh","deh","dah","udah","sih","tuh","dong",
    "ga","gak","nggak","ngga","gk","kok","nih","tapi","tp","buat","bwt",
}

POS_SEED = {
    "mantap","mantul","keren","bagus","sip","oke","ok","nice","kawaii","suki","sugoi",
    "asik","asyik","kocak","ngakak","lucu","gokil","gokill","mantapp","mantapuu",
    "gaskeun","gasken","gas","cihuy","ciyus","anjay","auto","win","mantappu",
    "wkwk","wk","wkwkwk","www","haha","hahaha","lol","lolol",
    "anjayy","santuy","santuyy","ciamik","kerenbet","btul","betul",
}
NEG_SEED = {
    "gaje","jelek","ampas","burik","buruk","apasi","apaan","gabut","meh","mehhd",
    "norak","alay","lebay","gajelas","gajls","gajelas","anjirlah","booring","bosen",
    "gaklucu","galucu","notsmart","nfunny","ngebetein","bete","bt","apalah",
}

def _ensure_db():
    d = os.path.dirname(DB_PATH)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS slang_lexicon (
            token TEXT PRIMARY KEY,
            pos INTEGER DEFAULT 0,
            neg INTEGER DEFAULT 0,
            updated_ts INTEGER
        )""")
        for t in POS_SEED:
            cur.execute("INSERT OR IGNORE INTO slang_lexicon(token,pos,neg,updated_ts) VALUES (?,?,?,?)",
                        (t, 1, 0, int(time.time())))
        for t in NEG_SEED:
            cur.execute("INSERT OR IGNORE INTO slang_lexicon(token,pos,neg,updated_ts) VALUES (?,?,?,?)",
                        (t, 0, 1, int(time.time())))
        con.commit()
    finally:
        con.close()

def _tokens(text: str) -> Iterable[str]:
    for m in TOKEN_RE.finditer(text.lower()):
        tok = m.group(0)
        if tok and tok not in STOP and not tok.isdigit():
            tok = re.sub(r"(.)\1{2,}", r"\1\1", tok)
            yield tok

def score_text(text: str) -> Tuple[int, int]:
    _ensure_db()
    toks = list(_tokens(text))
    if not toks:
        return (0, 0)
    qmarks = ",".join("?" for _ in toks)
    con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
    try:
        cur = con.cursor()
        cur.execute(f"SELECT token,pos,neg FROM slang_lexicon WHERE token IN ({qmarks})", toks)
        pos = neg = 0
        for r in cur.fetchall():
            pos += int(r["pos"] > 0)
            neg += int(r["neg"] > 0)
        return (pos, neg)
    finally:
        con.close()

def learn_from_text(text: str, is_positive: bool | None):
    if is_positive is None:
        return
    _ensure_db()
    toks = [t for t in _tokens(text) if 2 <= len(t) <= 14]
    if not toks:
        return
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.cursor()
        for t in toks:
            if is_positive:
                cur.execute("""INSERT INTO slang_lexicon(token,pos,neg,updated_ts)
                               VALUES (?,?,?,?)
                               ON CONFLICT(token) DO UPDATE SET
                               pos = pos + 1,
                               updated_ts = excluded.updated_ts""", (t,1,0,int(time.time())))
            else:
                cur.execute("""INSERT INTO slang_lexicon(token,pos,neg,updated_ts)
                               VALUES (?,?,?,?)
                               ON CONFLICT(token) DO UPDATE SET
                               neg = neg + 1,
                               updated_ts = excluded.updated_ts""", (t,0,1,int(time.time())))
        con.commit()
    finally:
        con.close()
