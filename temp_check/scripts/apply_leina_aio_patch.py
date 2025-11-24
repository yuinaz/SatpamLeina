
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LEINA AIO PATCH v4 — merge-only overrides, Upstash indent fixer, and full wiring fixes.

Run from repo root:
  python scripts/apply_leina_aio_patch.py
"""
import os, re, json, shutil, pathlib

ROOT = pathlib.Path(".")
LOG = print

def _read(p: pathlib.Path):
    return p.read_text(encoding="utf-8")

def _write(p: pathlib.Path, s: str):
    p.write_text(s, encoding="utf-8")

def _ok(x): LOG("[OK] " + x)
def _info(x): LOG("[INFO] " + x)
def _warn(x): LOG("[WARN] " + x)

# ---------- helpers ----------
def _inject_guard(text: str, func: str, ret: str):
    pat = re.compile(rf"(async\s+def\s+{func}\s*\([^)]*\)\s*:\s*)", re.M)
    def _ins(m):
        # compute indent of first body line
        i = m.end()
        indent = ""
        while i < len(text) and text[i] != "\n": i += 1
        j = i + 1
        while j < len(text) and text[j] in (" ", "\t"):
            indent += ("    " if text[j] == "\t" else " "); j += 1
        guard = (f"{indent}import os\n"
                 f"{indent}if os.getenv('LEINA_SHUTTING_DOWN') == '1':\n"
                 f"{indent}    return {ret}\n")
        return m.group(0) + "\n" + guard
    return pat.sub(_ins, text, count=1)

def normalize_indentation(code: str) -> str:
    # Convert tabs to 4 spaces & fix trailing spaces
    lines = code.splitlines()
    out = []
    for ln in lines:
        # replace leading tabs with 4 spaces
        i = 0
        while i < len(ln) and ln[i] in (' ', '\t'):
            i += 1
        lead = ln[:i].replace('\t', '    ')
        rest = ln[i:]
        out.append(lead + rest.rstrip())
    return "\n".join(out) + "\n"

# ---------- 1) merge overrides (no overwrite) ----------
def patch_overrides_merge():
    p = ROOT / "data/config/overrides.render-free.json"
    if not p.is_file():
        _warn("overrides.render-free.json not found; skipping")
        return 0
    # backup once
    bak = p.with_suffix(".json.bak")
    if not bak.exists():
        shutil.copy2(p, bak)
        _ok(f"backup created: {bak.name}")
    j = json.loads(_read(p))
    env = dict(j.get("env", {}))

    # Only update/set these keys; keep the rest untouched
    updates = {
        # QnA core
        "QNA_ENABLE": "1",
        "QNA_INTERVAL_SEC": env.get("QNA_INTERVAL_SEC", "180"),
        "QNA_AUTOLEARN_ENABLE": "1",
        "QNA_AUTOLEARN_PERIOD_SEC": env.get("QNA_AUTOLEARN_PERIOD_SEC", "180"),
        "QNA_BOOT_KICK": env.get("QNA_BOOT_KICK", "0"),
        # Titles
        "QNA_TITLE_ISOLATION": "Question by Leina",
        "QNA_TITLE_PUBLIC": env.get("QNA_TITLE_PUBLIC", "Answer by Leina"),
        "QNA_EMBED_TITLE_LEINA": "Question by Leina",
        "QNA_EMBED_TITLE_PROVIDER": "Answer by {provider}",
        # Providers
        "QNA_PROVIDER_ORDER": env.get("QNA_PROVIDER_ORDER", "gemini,groq"),
        "QNA_FORCE_PROVIDER": env.get("QNA_FORCE_PROVIDER", ""),
        "QNA_STRICT_FORCE": env.get("QNA_STRICT_FORCE", "1"),
        "GEMINI_FORCE_DISABLE": env.get("GEMINI_FORCE_DISABLE", "0"),
        "GROQ_FORCE_DISABLE": env.get("GROQ_FORCE_DISABLE", "0"),
        "LLM_GEMINI_MODEL": env.get("LLM_GEMINI_MODEL", "gemini-2.5-flash-lite"),
        "LLM_GROQ_MODEL": env.get("LLM_GROQ_MODEL", "llama-3.1-8b-instant"),
        # Shadow
        "SHADOW_ENABLE": env.get("SHADOW_ENABLE", "1"),
        "DISABLE_DUPLICATE_QNA": env.get("DISABLE_DUPLICATE_QNA", "1"),
    }
    env.update(updates)

    # Clean COGS_ALWAYS but preserve others
    raw = env.get("COGS_ALWAYS", "") or ""
    mods = [m.strip() for m in raw.split(",") if m.strip()]
    seen, clean = set(), []
    for m in mods:
        if m in seen: continue
        seen.add(m); clean.append(m)
    off = {
        "satpambot.bot.modules.discord_bot.cogs.a00_render_runtime_guard",
        "satpambot.bot.modules.discord_bot.cogs.a00_hotenv_autoreload_overlay",
    }
    clean = [m for m in clean if m not in off]
    main = "satpambot.bot.modules.discord_bot.cogs.a08_shadow_learning_observer_overlay"
    alt  = "satpambot.bot.modules.discord_bot.cogs.a08s_shadow_learning_observer_overlay"
    if main in clean and alt in clean:
        clean = [m for m in clean if m != alt]
        _info("removed alt shadow observer from COGS_ALWAYS")
    env["COGS_ALWAYS"] = ",".join(clean)

    j["env"] = env
    _write(p, json.dumps(j, ensure_ascii=False, indent=2))
    _ok("overrides.render-free.json merged (safe, non-destructive)")
    return 1

# ---------- 2) fix upstash client & guards ----------
def patch_upstash_and_indent():
    p = ROOT / "satpambot/bot/modules/discord_bot/helpers/upstash_client.py"
    if not p.is_file(): 
        _warn("helpers/upstash_client.py not found; skipping")
        return 0
    s = normalize_indentation(_read(p))
    # Inject shutdown guards
    s = _inject_guard(s, "_aget", "None")
    s = _inject_guard(s, "_apost", "None")
    _write(p, s)
    _ok("helpers/upstash_client.py normalized & guarded")
    # Presence overlay: optional guard
    po = ROOT / "satpambot/bot/modules/discord_bot/cogs/a09_presence_from_upstash_overlay.py"
    if po.is_file():
        t = _read(po)
        if "LEINA_UPSTASH_SAFE" not in t:
            t += (
                "\n# LEINA_UPSTASH_SAFE: skip overlay if missing config\n"
                "import os as _os\n"
                "if not (_os.getenv('UPSTASH_URL') and _os.getenv('UPSTASH_TOKEN')):\n"
                "    ENABLE = False\n"
            )
            _write(po, normalize_indentation(t))
            _ok(f"{po.name} guarded for missing config")
    return 1

# ---------- 3) xp mirror pins guard ----------
def patch_xp_mirror():
    p = ROOT / "satpambot/bot/modules/discord_bot/cogs/a08_xp_event_dual_mirror_bridge.py"
    if not p.is_file(): return 0
    s = _read(p)
    if "_leina_safe_pins" not in s:
        s += (
            "\n\nasync def _leina_safe_pins(ch, log=None):\n"
            "    try:\n        return await ch.pins()\n"
            "    except Exception as e:\n"
            "        status = getattr(e, 'status', None)\n"
            "        name = getattr(getattr(e, '__class__', None), '__name__', 'Exception')\n"
            "        if status == 403 or name in ('Forbidden',):\n"
            "            if log:\n                cid = getattr(ch, 'id', '?')\n"
            "                log.warning('[xp-mirror] pin fetch forbidden ch=%s (50001) → skip', cid)\n"
            "            return []\n"
            "        if log: log.warning('[xp-mirror] pin fetch failed: %r', e)\n"
            "        return []\n"
        )
    s = re.sub(r"await\s+([A-Za-z0-9_\.]+)\.pins\(\)", r"await _leina_safe_pins(\1, log)", s)
    _write(p, s); _ok(f"{p.name} pins() hardened")
    return 1

# ---------- 4) shadow anti-skip ----------
def patch_shadow():
    total = 0
    for name in ("a08_shadow_learning_observer_overlay.py","a08s_shadow_learning_observer_overlay.py"):
        p = ROOT / f"satpambot/bot/modules/discord_bot/cogs/{name}"
        if not p.is_file(): continue
        s = _read(p)
        s = re.sub(r"try:\s*\n\s*qna\s*=\s*int\([^)]*QNA_CHANNEL_ID[^)]*\)[\s\S]*?except\s+Exception:\s*pass",
                   "try:\n    pass\nexcept Exception:\n    pass", s, flags=re.M)
        if "LEINA PATCH: allow award in QNA channel" not in s:
            s += ("\n# LEINA PATCH: allow award in QNA channel\n"
                  "try:\n"
                  "    import os\n"
                  "    _qna = int(os.getenv('QNA_CHANNEL_ID','0'))\n"
                  "    if _qna:\n"
                  "        for _n in ['SKIP','SKIP_IDS','SKIP_CHANNELS']:\n"
                  "            if _n in globals():\n"
                  "                _s = globals()[_n]\n"
                  "                try: _s.discard(_qna)\n"
                  "                except Exception:\n"
                  "                    try:\n"
                  "                        if _qna in _s: del _s[_qna]\n"
                  "                    except Exception:\n"
                  "                        pass\n"
                  "except Exception:\n"
                  "    pass\n")
        _write(p, s); _ok(f"{p.name} shadow anti-skip applied")
        total += 1
    return total

# ---------- 5) QnA flow ----------
def patch_qna_flow():
    # Scheduler -> Question by Leina
    p = ROOT / "satpambot/bot/modules/discord_bot/cogs/a24_qna_autolearn_scheduler.py"
    if p.is_file():
        s = _read(p)
        if "TITLE_ASK" not in s:
            s = s.replace('TITLE_PUB = os.getenv("QNA_TITLE_PUBLIC", "Answer by Leina")',
                          'TITLE_PUB = os.getenv("QNA_TITLE_PUBLIC", "Answer by Leina")\nTITLE_ASK = os.getenv("QNA_EMBED_TITLE_LEINA", os.getenv("QNA_TITLE_ISOLATION", "Question by Leina"))')
        s = s.replace("discord.Embed(title=TITLE_ISO, description=topic)",
                      "discord.Embed(title=TITLE_ASK, description=topic)")
        _write(p, s); _ok(f"{p.name} question uses TITLE_ASK")
    # Answer -> Answer by {provider}
    p = ROOT / "satpambot/bot/modules/discord_bot/cogs/a06_autolearn_qna_answer_overlay.py"
    if p.is_file():
        s = _read(p)
        s = re.sub(
            r"emb2\s*=\s*discord\.Embed\(title\s*=.*?description\s*=\s*text\)",
            'from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_str as _cfg\n            _title = str(_cfg("QNA_EMBED_TITLE_PROVIDER","Answer by {provider}")).format(provider=provider or "Leina")\n            emb2 = discord.Embed(title=_title, description=text)',
            s,
            flags=re.S
        )
        s = re.sub(r'emb2\.set_footer\(.*?\)', 'emb2.set_footer(text=f"[QNA][PROVIDER:{provider}]")', s)
        _write(p, s); _ok(f"{p.name} answer uses provider title + markers")
    return 1

def main():
    patch_overrides_merge()
    patch_upstash_and_indent()
    patch_xp_mirror()
    patch_shadow()
    patch_qna_flow()
    _ok("AIO v4 applied (merge-only & indent fixed)")

if __name__ == "__main__":
    main()
