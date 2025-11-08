#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# LeinaP44 "penyakit" full smoke:
# - Overrides sanity (QnA titles, watchers, cogs include/exclude)
# - Provider resolver matrix (force/strict/disable/order)
# - QnA title/footer helpers output
# - Hotenv change-gate behavior
# - XP pin target presence
# - Dedup config
# - Upstash connectivity (optional; skip if URL/TOKEN missing)
# This script is safe to run locally; it DOES NOT call Discord/Groq/Gemini.
import os, sys, json, pathlib, importlib, traceback

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent  # project root when placed at repo root/scripts
OVERRIDES_PATH = os.getenv("SMOKE_OVERRIDES_PATH") or str(ROOT / "data/config/overrides.render-free.json")

_failures = []
_warnings = []

def fail(name, msg):
    _failures.append((name, msg))

def warn(name, msg):
    _warnings.append((name, msg))

def ok(msg):
    print("  ✔", msg)

def load_overrides():
    p = pathlib.Path(OVERRIDES_PATH)
    if not p.is_file():
        fail("overrides", f"Overrides file not found: {p}")
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        env = data.get("env", {}) if isinstance(data, dict) else {}
        if not isinstance(env, dict):
            fail("overrides", "env is not a dict")
            return {}
        print(f"[overrides] loaded: {p}")
        return env
    except Exception as e:
        fail("overrides", f"failed to parse: {e}")
        return {}

def check_overrides(env):
    # Titles
    if "{provider}" in (env.get("QNA_TITLE_ISOLATION","").lower()):
        fail("qna_title", "QNA_TITLE_ISOLATION contains {provider} literal")
    else:
        ok("QNA_TITLE_ISOLATION ok")
    # Watcher: only overrides/.env
    files = (env.get("HOTENV_WATCH_FILES","") or "").replace(";",",")
    if "runtime_env.json" in files:
        fail("hotenv_watch", "HOTENV_WATCH_FILES contains runtime_env.json (should be overrides only)")
    else:
        ok("HOTENV_WATCH_FILES ok (no runtime_env.json)")
    globs = (env.get("HOTENV_WATCH_GLOBS","") or "").replace(";",",")
    if globs and "runtime_env.json" in globs:
        fail("hotenv_glob", "HOTENV_WATCH_GLOBS contains runtime_env.json")
    else:
        ok("HOTENV_WATCH_GLOBS ok")
    # Broadcast
    if (env.get("HOTENV_BROADCAST_EVENT","1") != "0"):
        warn("hotenv_broadcast", "HOTENV_BROADCAST_EVENT not 0 (can cause reload chatter)")
    else:
        ok("HOTENV_BROADCAST_EVENT=0")
    # COGS ALWAYS include/exclude
    always = [p.strip() for p in (env.get("COGS_ALWAYS","") or "").split(",") if p.strip()]
    incl = [
        "satpambot.bot.modules.discord_bot.cogs.a24b_qna_dual_mode_markers_overlay",
        "satpambot.bot.modules.discord_bot.cogs.a00_qna_force_lock_overlay",
        "satpambot.bot.modules.discord_bot.cogs.a00_disable_duplicate_qna_overlay",
        "satpambot.bot.modules.discord_bot.cogs.a00_env_hybrid_overlay",
    ]
    excl = [
        ".a00_graceful_shutdown_overlay",
        ".a00_hotenv_autoreload_overlay",
    ]
    for i in incl:
        if not any(x==i for x in always):
            fail("cogs_always_missing", f"COGS_ALWAYS missing: {i}")
    for s in excl:
        if any(x.endswith(s) for x in always):
            fail("cogs_always_exclude", f"COGS_ALWAYS should NOT include *{s}")
    ok("COGS_ALWAYS include/exclude checks done")
    # XP pin
    if not env.get("XP_STAGE_PIN_CHANNEL_ID"): fail("xp_pin","XP_STAGE_PIN_CHANNEL_ID missing")
    if not env.get("XP_STAGE_PIN_MESSAGE_ID"): fail("xp_pin","XP_STAGE_PIN_MESSAGE_ID missing")
    if env.get("XP_STAGE_STRICT_EDIT_ONLY","1") != "1": warn("xp_pin","STRICT_EDIT_ONLY not 1")
    else: ok("XP pin targets present")
    # Dedup
    if env.get("DISABLE_DUPLICATE_QNA","1") != "1":
        warn("qna_dedup","DISABLE_DUPLICATE_QNA not 1")
    else:
        ok("QnA dedup enabled")

def import_module(mod):
    try:
        return importlib.import_module(mod), None
    except Exception as e:
        return None, e

def check_provider_resolver():
    # patches.qna_env_resolver must exist
    sys.path.insert(0, str(ROOT))  # ensure repo root on sys.path
    mod, err = import_module("patches.qna_env_resolver")
    if err:
        fail("resolver_import", f"Cannot import patches.qna_env_resolver: {err}")
        return
    sel = getattr(mod, "select_qna_provider", None)
    if not callable(sel):
        fail("resolver_api", "select_qna_provider() not found")
        return

    def run(envset, expect):
        keep = {}
        # backup and set
        for k,v in envset.items():
            keep[k] = os.environ.get(k)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = str(v)
        try:
            p, via = sel()
            ok(f"resolver {envset} -> ({p},{via})")
            exp_p = expect.get("provider")
            exp_via = expect.get("via")
            if exp_p and p != exp_p:
                fail("resolver_matrix", f"expected provider={exp_p} got {p} for env={envset}")
            if exp_via and via != exp_via:
                fail("resolver_matrix", f"expected via={exp_via} got {via} for env={envset}")
        finally:
            # restore
            for k,v in keep.items():
                if v is None: os.environ.pop(k, None)
                else: os.environ[k] = v

    # Matrix: order + disable, forced w/ strict
    run({"QNA_PROVIDER_ORDER":"gemini,groq","GEMINI_FORCE_DISABLE":"0","GROQ_FORCE_DISABLE":"1"}, {"provider":"gemini","via":"order"})
    run({"QNA_FORCE_PROVIDER":"groq","QNA_STRICT_FORCE":"1","GROQ_FORCE_DISABLE":"0"}, {"provider":"groq","via":"forced"})
    run({"QNA_FORCE_PROVIDER":"groq","QNA_STRICT_FORCE":"1","GROQ_FORCE_DISABLE":"1"}, {"provider":"gemini","via":"order"})  # forced disabled -> fallback to order

def check_qna_helpers():
    sys.path.insert(0, str(ROOT))
    mod, err = import_module("satpambot.bot.modules.discord_bot.cogs.a24_qna_auto_answer_overlay_helpers")
    if err:
        fail("helpers_import", f"cannot import helpers: {err}")
        return
    qtitle = getattr(mod, "qna_title", None)
    fmk = getattr(mod, "footer_markers", None)
    if not callable(qtitle) or not callable(fmk):
        fail("helpers_api", "qna_title/footer_markers missing")
        return
    # Title no raw {provider}
    os.environ["QNA_TITLE_ISOLATION"] = "Answer by Leina"
    t = qtitle("gemini")
    if "{provider}" in t.lower():
        fail("qna_title_logic", f"unexpected title: {t}")
    else:
        ok(f"title -> {t}")
    # Footer markers
    os.environ["QNA_PROVIDER_ORDER"] = "gemini,groq"
    m = fmk("gemini")
    if "[QNA]" not in m or "PROVIDER:gemini" not in m or "MODE:primary" not in m:
        fail("qna_footer_markers", f"bad markers: {m}")
    else:
        ok("footer markers ok")

def check_hotenv_gate():
    sys.path.insert(0, str(ROOT))
    mod, err = import_module("satpambot.bot.modules.discord_bot.cogs.a00_hotenv_change_gate_overlay")
    if err:
        fail("hotenv_gate_import", f"cannot import change-gate: {err}")
        return
    fn = getattr(mod, "apply_change", None)
    if not callable(fn):
        fail("hotenv_gate_api", "apply_change not found")
        return
    # no diff -> False
    res = fn({"A":"1"},{"A":"1"})
    if res:
        fail("hotenv_gate", "expected False on no-diff")
    else:
        ok("hotenv gate: no-diff -> False")
    res2 = fn({"A":"1"},{"A":"2"})
    if not res2:
        fail("hotenv_gate", "expected True on diff")
    else:
        ok("hotenv gate: diff -> True")

def check_xp_pin_env(env):
    ch = env.get("XP_STAGE_PIN_CHANNEL_ID")
    msg = env.get("XP_STAGE_PIN_MESSAGE_ID")
    if not (str(ch).isdigit() and str(msg).isdigit()):
        fail("xp_pin_ids", f"pin ids invalid: ch={ch} msg={msg}")
    else:
        ok(f"xp pin ids ok (ch={ch} msg={msg})")

def check_dedup_env(env):
    if env.get("DISABLE_DUPLICATE_QNA","1") != "1":
        fail("qna_dedup_env", "DISABLE_DUPLICATE_QNA should be 1")
    else:
        ok("qna dedup env ok")

def check_upstash_connectivity():
    # optional: only if url/token present
    url = (os.getenv("UPSTASH_REDIS_REST_URL") or os.getenv("UPSTASH_REST_URL") or "").strip()
    tok = (os.getenv("UPSTASH_REDIS_REST_TOKEN") or os.getenv("UPSTASH_REST_TOKEN") or "").strip()
    if not url or not tok:
        warn("upstash", "URL/TOKEN missing -> skip connectivity test")
        return
    try:
        import httpx, asyncio
    except Exception as e:
        warn("upstash", f"httpx not available -> skip ({e})")
        return
    async def _go():
        async with httpx.AsyncClient(timeout=10) as cli:
            r = await cli.post(url.rstrip('/')+"/pipeline", headers={"Authorization": f"Bearer {tok}"}, json=[["PING"]])
            return r.status_code
    try:
        code = asyncio.run(_go())
        if code >= 400:
            fail("upstash_conn", f"HTTP {code} from pipeline")
        else:
            ok("upstash connectivity OK")
    except Exception as e:
        fail("upstash_conn", f"error: {e}")

def main():
    print("== LeinaP44 Penyakit Smoke ==")
    env = load_overrides()
    if env:
        check_overrides(env)
        check_xp_pin_env(env)
        check_dedup_env(env)
    check_provider_resolver()
    check_qna_helpers()
    check_hotenv_gate()
    check_upstash_connectivity()

    print("\n== RESULT ==")
    if _warnings:
        print(f"Warnings ({len(_warnings)}):")
        for n,m in _warnings:
            print("  -", n, ":", m)
    if _failures:
        print(f"FAIL ({len(_failures)}):")
        for n,m in _failures:
            print("  -", n, ":", m)
        sys.exit(1)
    print("PASS: all checks green")
    sys.exit(0)

if __name__ == "__main__":
    main()
