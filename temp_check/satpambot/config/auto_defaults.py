
# Auto defaults used across modules
DEFAULTS = {
    "XP_SENIOR_KEY": "xp:bot:senior_total",
}
def cfg_str(k, d=""):
    import os
    return os.getenv(k, DEFAULTS.get(k, d))
def cfg_int(k, d=0):
    import os
    try: return int(os.getenv(k, str(d)))
    except Exception: return d
