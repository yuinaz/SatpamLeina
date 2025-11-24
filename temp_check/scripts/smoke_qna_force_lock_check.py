import os, importlib

def peek_mod_attr(mod, names):
    try:
        m = importlib.import_module(mod)
    except Exception:
        return {}
    out = {}
    for n in names:
        out[n] = getattr(m, n, None)
    return out

keys = ["QNA_FORCE_PROVIDER","QNA_STRICT_FORCE","QNA_PROVIDER_PRIORITY",
        "GEMINI_FORCE_DISABLE","GROQ_FORCE_DISABLE",
        "QNA_ALLOW_FALLBACK","QNA_ALLOW_FALLBACK_WHEN_FORCED",
        "QNA_AUTOFALLBACK","QNA_AUTOFAILOVER","QNA_AUTOPILOT"]
print("[LOCK-SMOKE] env:")
for k in keys:
    print(f"  {k}={os.getenv(k)}")

# known overlays (best-effort)
mods = [
  "satpambot.bot.modules.discord_bot.cogs.a00_qna_provider_autofailover_local_overlay",
  "satpambot.bot.modules.discord_bot.cogs.a00_qna_provider_autofailover_quota_overlay",
  "satpambot.bot.modules.discord_bot.cogs.a24_qna_autopilot_scheduler",
]
for m in mods:
    st = peek_mod_attr(m, ["ENABLE","ENABLED","ACTIVE","Active"])
    if st:
        print(f"[LOCK-SMOKE] {m} flags -> {st}")