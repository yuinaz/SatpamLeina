#!/usr/bin/env python3
import argparse, json, os, re, time, uuid
from typing import Dict, Optional, Tuple, Iterable

SEARCH_DIRS = [".","./satpambot","./satpambot/bot/modules/discord_bot","./satpambot/bot/modules/discord_bot/config","./data","./data/config"]
ENV_FILES = [".env","satpambot/.env"]
OVERRIDE_FILES = ["overrides.render-free.json","satpambot/overrides.render-free.json","satpambot/bot/modules/discord_bot/overrides.render-free.json","data/config/overrides.render-free.json"]
RUNTIME_FILES = ["runtime_env.json","satpambot/runtime_env.json","satpambot/bot/modules/discord_bot/config/runtime_env.json","data/config/runtime_env.json"]

def _find_first(paths: Iterable[str]) -> Optional[str]:
    for p in paths:
        if os.path.isfile(p):
            return p
    for base in SEARCH_DIRS:
        for name in paths:
            candidate = os.path.join(base, os.path.basename(name))
            if os.path.isfile(candidate):
                return candidate
    return None

def _flatten(obj, prefix="", out=None):
    if out is None:
        out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            _flatten(v, f"{prefix}{k}." if prefix else f"{k}.", out)
    elif isinstance(obj, list):
        # ignore arrays
        pass
    else:
        key = prefix[:-1] if prefix.endswith(".") else prefix
        if key:
            out[key] = "" if obj is None else str(obj)
    return out

def _load_env_file(path: str) -> Dict[str,str]:
    kv = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                m = re.match(r'^([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*(.*)$', s)
                if not m:
                    continue
                k, v = m.group(1), m.group(2)
                if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                    v = v[1:-1]
                kv[k] = v
    except Exception:
        pass
    return kv

def _load_json_flat(path: str) -> Dict[str,str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        flat = _flatten(data)
        envish = {k: v for k, v in flat.items() if "." not in k}
        return envish if envish else flat
    except Exception:
        return {}

def _export_kv_to_env(d: Dict[str,str], merged: Dict[str,str]):
    for k, v in d.items():
        kk = k.split(".",1)[1] if k.lower().startswith("env.") else k
        if kk not in os.environ or os.environ[kk] == "":
            os.environ[kk] = v
            merged[kk] = v

def env_hybrid_export(verbose=True) -> Dict[str,str]:
    merged = {}
    rt = _find_first(RUNTIME_FILES)
    if rt:
        _export_kv_to_env(_load_json_flat(rt), merged)
        if verbose:
            print(f"[env-hybrid] loaded runtime: {rt} -> merged")
    else:
        if verbose:
            print("[env-hybrid] runtime_env.json not found")
    ov = _find_first(OVERRIDE_FILES)
    if ov:
        _export_kv_to_env(_load_json_flat(ov), merged)
        if verbose:
            print(f"[env-hybrid] loaded overrides: {ov} -> merged")
    else:
        if verbose:
            print("[env-hybrid] overrides.render-free.json not found")
    envp = _find_first(ENV_FILES)
    if envp:
        _export_kv_to_env(_load_env_file(envp), merged)
        if verbose:
            print(f"[env-hybrid] loaded .env: {envp} -> merged")
    else:
        if verbose:
            print("[env-hybrid] .env not found")
    if verbose:
        preview = {k: merged[k] for k in list(merged.keys())[:8]}
        print(f"[env-hybrid] exported {len(merged)} keys; preview={preview}")
    return merged

def llm_availability_env() -> dict:
    gem_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    grq_key = os.getenv("GROQ_API_KEY") or ""
    gem_model = os.getenv("GEMINI_MODEL","")
    grq_model = os.getenv("GROQ_MODEL","")
    warn = []
    if gem_key and not gem_model: warn.append("GEMINI_MODEL missing")
    if grq_key and not grq_model: warn.append("GROQ_MODEL missing")
    return {
        "gemini": bool(gem_key.strip()),
        "groq": bool(grq_key.strip()),
        "gemini_model": gem_model,
        "groq_model": grq_model,
        "warning": "; ".join(warn)
    }

try:
    import requests
except Exception:
    requests = None

def _env(k, d=None):
    return os.getenv(k, d)

def _pick_token():
    return (_env("DISCORD_TOKEN")
            or _env("BOT_TOKEN")
            or _env("DISCORD_BOT_TOKEN")
            or _env("LEINA_BOT_TOKEN"))

def _discord_headers(t):
    return {"Authorization": f"Bot {t}", "Content-Type":"application/json"}

def _discord_get_me(t):
    r = requests.get("https://discord.com/api/v10/users/@me", headers=_discord_headers(t), timeout=15)
    r.raise_for_status()
    return r.json()

def _discord_send_embed(t, c, title, desc, footer):
    payload = {"embeds":[{"title":title,"description":desc,"footer":{"text":footer}}]}
    r = requests.post(f"https://discord.com/api/v10/channels/{c}/messages",
                      headers=_discord_headers(t), data=json.dumps(payload), timeout=20)
    r.raise_for_status()
    return r.json()

def _discord_list_messages(t, c, limit=30):
    r = requests.get(f"https://discord.com/api/v10/channels/{c}/messages?limit={limit}",
                     headers=_discord_headers(t), timeout=20)
    r.raise_for_status()
    return r.json()

def _find_answer(msgs, bot_id):
    for m in msgs:
        if str(m.get("author",{}).get("id")) != str(bot_id):
            continue
        for e in (m.get("embeds") or []):
            title = (e.get("title") or "").strip()
            if title.lower().startswith("answer by"):
                prov = title.split("by",1)[-1].strip()
                if prov:
                    return prov, m.get("id")
    return None

def run_channel_flow_check(channel_id, timeout_sec=45):
    if not requests:
        print("[CHANNEL] SKIP: 'requests' not available.")
        return (False, None)
    tok = _pick_token()
    if not tok:
        print("[CHANNEL] SKIP: No DISCORD bot token found.")
        return (False, None)
    try:
        me = _discord_get_me(tok)
        bot_id = str(me["id"])
    except Exception as e:
        print(f"[CHANNEL] FAIL: cannot query /users/@me -> {e}")
        return (False, None)
    smoke = f"smoke:{uuid.uuid4().hex[:8]}"
    prompt = "Sebutkan satu fakta singkat tentang kopi. Jawab ringkas (≤20 kata)."
    try:
        _discord_send_embed(tok, channel_id, "Question by Leina", prompt, smoke)
    except Exception as e:
        print(f"[CHANNEL] FAIL: cannot POST question -> {e}")
        return (False, None)
    deadline = time.time() + timeout_sec
    print(f"[CHANNEL] waiting up to {timeout_sec}s for 'Answer by <PROVIDER>'...")
    while time.time() < deadline:
        try:
            msgs = _discord_list_messages(tok, channel_id, limit=25)
            ans = _find_answer(msgs, bot_id)
            if ans:
                prov, mid = ans
                print(f"[CHANNEL] Answer detected from provider={prov} (message_id={mid})")
                return (True, prov)
        except Exception as e:
            print(f"[CHANNEL] WARN: polling failed -> {e}")
        time.sleep(2.0)
    print("[CHANNEL] FAIL: timeout waiting for answer")
    return (False, None)

def resolve_channel_id(cli: Optional[str]):
    if cli:
        return cli, "--channel"
    for key in ["QNA_AUTOLEARN_CHANNEL_ID","QNA_CHANNEL_ID","QNA_PRIVATE_ID","QNA_PUBLIC_ID"]:
        v = os.getenv(key)
        if v:
            return v, key
    return None, ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", default=None)
    ap.add_argument("--timeout", type=int, default=int(os.getenv("TIMEOUT_SEC","45")))
    ap.add_argument("--no-channel", action="store_true")
    args = ap.parse_args()

    env_hybrid_export(verbose=True)

    print("== LLM AVAILABILITY (env-hybrid) ==")
    avail = llm_availability_env()
    print(f"GEMINI available? {avail['gemini']}  model={avail['gemini_model'] or '-'}")
    print(f"GROQ   available? {avail['groq']}  model={avail['groq_model'] or '-'}")
    if avail["warning"]:
        print(f"WARNING: {avail['warning']}")

    overall = True
    cid, source = resolve_channel_id(args.channel)
    if not args.no_channel and cid:
        print(f"\n== CHANNEL FLOW CHECK (source={source}) ==")
        ok, prov = run_channel_flow_check(cid, timeout_sec=args.timeout)
        overall = overall and ok
        if ok:
            print("CHANNEL_OK provider=" + str(prov))
        else:
            print("CHANNEL_FAIL")
    else:
        print("\n== CHANNEL FLOW CHECK SKIPPED ==")
        if not cid:
            print("TIP: Provide --channel or set QNA_* env")

    if not overall:
        raise SystemExit(2)
    print("SMOKE_OK")

if __name__=="__main__":
    main()
