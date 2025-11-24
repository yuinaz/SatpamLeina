import os

def get(name: str, default=None): return os.getenv(name, default)
def get_bool(name: str, default: bool=False) -> bool:
    v = os.getenv(name)
    if v is None: return default
    return str(v).strip().lower() in ("1","true","yes","on","y")
def get_int(name: str, default: int) -> int:
    try: return int(os.getenv(name, str(default)))
    except: return default
def get_float(name: str, default: float) -> float:
    try: return float(os.getenv(name, str(default)))
    except: return default
def get_list(name: str, default_csv: str):
    raw = os.getenv(name, default_csv) or ""
    return [x.strip() for x in raw.split(",") if x.strip()]

def owner_id() -> int:
    try: return int(get("OWNER_USER_ID","228126085160763392"))
    except: return 228126085160763392

# Memory profile defaults to 'lite' for Render Free
def system_profile():
    return get("SYSTEM_PROFILE","lite").lower()

def _detect_total_ram_mb():
    try:
        import psutil
        return int(psutil.virtual_memory().total / (1024*1024))
    except Exception:
        try:
            import resource
            soft, _ = resource.getrlimit(resource.RLIMIT_AS)
            if soft > 0 and soft < 1<<60:
                return int(soft / (1024*1024))
        except Exception:
            pass
        return 2048

def memory_thresholds_mb():
    sof = get_int("MEMORY_GUARD_SOFT_MB", 0)
    har = get_int("MEMORY_GUARD_HARD_MB", 0)
    if sof and har: 
        return sof, har
    total = _detect_total_ram_mb()
    prof = system_profile()
    if prof == "full":
        soft = int(total * 0.85); hard = int(total * 0.92)
    elif prof == "lite":
        soft = max(256, int(total * 0.35)); hard = max(320, int(total * 0.45))
    elif prof == "balanced":
        soft = int(total * 0.60); hard = int(total * 0.72)
    else:  # auto -> same as balanced for override file
        soft = int(total * 0.60); hard = int(total * 0.72)
    if hard <= soft: hard = soft + 32
    return soft, hard

# Passthrough of other getters if this file overrides defaults only
def log_channel_id_raw(): return get("LOG_CHANNEL_ID") or get("LOG_CHANNEL_ID_RAW")
def sticker_pos_threshold(): return get_int("STICKER_POS_THRESHOLD", 2)
def sticker_neg_threshold(): return get_int("STICKER_NEG_THRESHOLD", 1)
def sticker_text_window_sec(): return get_int("STICKER_TEXT_WINDOW_SEC", 90)
def persona_tone(): return get("PERSONA_TONE","tsundere")
def persona_tsundere_level():
    try: return max(0, min(3, int(get("PERSONA_TSUNDERE_LEVEL","2"))))
    except: return 2
def persona_langs(): return get_list("PERSONA_LANGS","id,en,ja,zh")
def persona_emoji_level():
    try: return max(0, min(3, int(get("PERSONA_EMOJI_LEVEL","2"))))
    except: return 2
def persona_ja_romaji_pref(): return get_bool("PERSONA_JA_ROMAJI_PREFERRED", True)
def persona_human_rate():
    try: return max(0.0, min(1.0, float(get("PERSONA_HUMAN_RATE","0.7"))))
    except: return 0.7
def persona_gif_enabled(): 
    return get_bool("PERSONA_GIF_ENABLE", False) or bool(get("TENOR_API_KEY"))
def stickers_enabled(): return get_bool("STICKER_ENABLE", True)
def sticker_base_rate(): 
    v = os.getenv("STICKER_BASE_RATE")
    if v is not None:
        try: return max(0.0, min(1.0, float(v)))
        except: return 0.25
    return 0.25
def sticker_min_rate(): return get_float("STICKER_MIN_RATE", 0.05)
def sticker_max_rate(): return get_float("STICKER_MAX_RATE", 0.70)  # a bit lower for free plan
def stickers_for(emotion: str):
    generic = get_list("STICKER_IDS", "")
    if emotion == "happy": sp = get_list("STICKER_IDS_HAPPY", ""); return sp or generic
    if emotion == "sad": sp = get_list("STICKER_IDS_SAD", ""); return sp or generic
    if emotion == "angry": sp = get_list("STICKER_IDS_ANGRY", ""); return sp or generic
    sp = get_list("STICKER_IDS_NEUTRAL", ""); return sp or generic
def pos_emoji_names(): 
    return [s.strip().lower() for s in (get("POS_EMOJI_NAMES","laugh,joy,rofl,grin,haha,clap,party,tada,heart,hearts,ok,thumbsup,fire,100,lit")).split(",") if s.strip()]
def neg_emoji_names():
    return [s.strip().lower() for s in (get("NEG_EMOJI_NAMES","angry,rage,cry,disappointed,thumbsdown,poop")).split(",") if s.strip()]

# Boot + rollback toggles (pass-through defaults same as earlier overlay)
def boot_dm_online(): return get_bool("BOOT_DM_ONLINE", True)
def boot_auto_thread(): return get_bool("BOOT_AUTO_THREAD", True)
def boot_auto_rollback(): return get_bool("AUTO_ROLLBACK", True)
def rollback_admin_roles():
    raw = get("ROLLBACK_ADMIN_ROLES","")
    return [s.strip().lower() for s in raw.split(",") if s.strip()]
def rollback_enable_command(): return get_bool("ROLLBACK_ENABLE_COMMAND", True)
def rollback_allow_force(): return get_bool("ROLLBACK_ALLOW_FORCE", True)
def rollback_reload_after(): return get_bool("ROLLBACK_RELOAD_AFTER", True)
