import os, random
from .gif_helper import tenor_search, pick_emoji
from .lang_utils import detect_lang, kana_to_romaji
try:
    from ...config import envcfg
except Exception:
    envcfg = None

def _env(name, default): return os.getenv(name, default)

def cfg_tone(): 
    try: return envcfg.persona_tone() if envcfg else _env("PERSONA_TONE","tsundere").lower()
    except: return "tsundere"
def cfg_tsundere_level():
    if envcfg: return envcfg.persona_tsundere_level()
    try: return max(0, min(3, int(_env("PERSONA_TSUNDERE_LEVEL","2"))))
    except: return 2
def cfg_langs(): 
    if envcfg: return envcfg.persona_langs()
    return [s.strip() for s in _env("PERSONA_LANGS","id,en,ja,zh").split(",") if s.strip()]
def cfg_emoji_level():
    if envcfg: return envcfg.persona_emoji_level()
    try: return max(0, min(3, int(_env("PERSONA_EMOJI_LEVEL","2"))))
    except: return 2
def cfg_ja_romaji_pref(): 
    if envcfg: return envcfg.persona_ja_romaji_pref()
    return _env("PERSONA_JA_ROMAJI_PREFERRED","1") == "1"
def cfg_human_rate():
    if envcfg: return envcfg.persona_human_rate()
    try: return max(0.0, min(1.0, float(_env("PERSONA_HUMAN_RATE","0.7"))))
    except: return 0.7
def gif_enabled():
    if envcfg: return envcfg.persona_gif_enabled()
    return _env("PERSONA_GIF_ENABLE","") == "1" or bool(os.getenv("TENOR_API_KEY"))

def laughter(): return "www"

def _humanize(text: str) -> str:
    rate = cfg_human_rate()
    if random.random() > rate:
        return text
    fillers = ["hmm", "eto", "ano", "uh", "uhm"]
    if random.random() < 0.3:
        text = random.choice(fillers) + "... " + text
    tail = random.choice(["~", "...", ""])
    if tail and not text.endswith(("!", "?", ".", "~", "...")):
        text = text + " " + tail
    return text

def _tsun_lines(lang: str, emotion: str, lvl: int):
    if lang == "ja":
        base = {
            "happy": ["yoshi, ganbaro!","ii jan, wakatteru yo.","mou~ nandaka ureshii jan!"],
            "sad": ["mou... shinpai shiteru kara ne.","tonikaku, daijoubu.","chotto yasuminasai yo."],
            "angry": ["yamete yo... baka!","urusai! wakatteru kara!","mou, anta tte hontou ni...!"],
            "neutral": ["hmph... wakatteru yo.","mou... shikataganai na.","betsu ni, anta no tame janai n dakara!"],
        }
    elif lang == "id":
        base = {
            "happy": ["yaudah… bagus juga sih.","heh, lumayan pinter juga ya.","aku ikut seneng… dikit doang!"],
            "sad": ["…ya udah sini, aku bantu.","jangan sedih… aku ada kok.","istirahat dulu, dasar bandel."],
            "angry": ["ya ampun… bikin repot aja!","bikin kesel tau!","sekali lagi begitu, awas ya!"],
            "neutral": ["bukan buat kamu kok… hmph.","jangan GR, ya.","aku cuma kebetulan bantu aja!"],
        }
    elif lang == "en":
        base = {
            "happy": ["fine! that was kinda nice.","don't get cocky… but good job.","I'm… a bit proud, okay?"],
            "sad": ["…ugh, come here. I'll help.","don't be sad. I'm here, okay?","take a break, dummy."],
            "angry": ["seriously?! you're such a pain!","cut it out, idiot!","one more time and—hmph!"],
            "neutral": ["it's not like I did it for you, okay?","hmph… don't get the wrong idea.","fine, I'll do it."],
        }
    else:
        base = {
            "happy": ["不错…别得意忘形。","还行啦…","我…稍微有点开心。"],
            "sad": ["别难过…我在。","先休息一下吧。","过来…我帮你。"],
            "angry": ["真是麻烦！","别再这样了！","你给我注意点！"],
            "neutral": ["哼…别误会。","只是顺便帮一下而已。","我才不是为了你呢。"],
        }
    arr = base.get(emotion, base["neutral"])
    return " " + random.choice(arr[:max(1, min(len(arr), 1+lvl))])

def _emoji_for_emotion(emotion: str) -> str:
    if emotion == "happy": return random.choice(["🙂","😊","✨","😎","🎉"])
    if emotion == "sad": return random.choice(["😢","😞","🥺"])
    if emotion == "angry": return random.choice(["😠","😤","💢"])
    return random.choice(["🤖","💬","🧠"])

def choose_lang(user_text: str) -> str:
    d = detect_lang(user_text or "")
    allowed = cfg_langs()
    return d if d in allowed else (allowed[0] if allowed else "id")

def generate_reply(user_text: str, base_reply: str, emotion: str = "neutral"):
    lang = choose_lang(user_text)
    text = base_reply.strip()
    if lang == "ja" and cfg_ja_romaji_pref():
        text = kana_to_romaji(text)

    if cfg_tone() == "tsundere":
        text = text + _tsun_lines(lang, emotion, cfg_tsundere_level())

    if cfg_emoji_level() > 0:
        text = text + " " + _emoji_for_emotion(emotion)

    text = _humanize(text)
    if lang == "ja" and random.random() < 0.35:
        text = text + " " + laughter()

    gif = None
    if gif_enabled() and emotion in ("happy","angry","sad"):
        topic = {"happy":"happy","angry":"angry","sad":"sad"}[emotion]
        gif = tenor_search(topic) or None
    return text, gif
