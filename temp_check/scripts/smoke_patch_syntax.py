#!/usr/bin/env python3
"""
Full‑online QNA smoke (inject overlays) + Provider Preflight Debug.

- Loads .env (if present)
- Preflight Groq: env presence + HTTPS probe to /openai/v1/models
- Forces provider via ENV hints when --provider is passed
- Injects a24_qna_auto_answer_overlay into the same process
- Prints [WAIT] logs until timeout

Usage:
  python scripts/smoke_patch_syntax.py --channel 1426571542627614772 --provider Groq --timeout 60
"""
import argparse, asyncio, os, sys, time, json, ssl, urllib.request

try:
    import discord
    from discord.ext import commands
except Exception as e:
    print("[FAIL] discord.py not installed:", e, file=sys.stderr); sys.exit(2)

def _load_local_env(paths=None):
    if paths is None: paths = [".env", "env/.env", "config/.env", "data/.env"]
    for p in paths:
        try:
            if not os.path.exists(p): continue
            with open(p, "r", encoding="utf-8") as fh:
                for line in fh:
                    s = line.strip()
                    if not s or s.startswith("#") or "=" not in s: continue
                    k, v = s.split("=", 1); k, v = k.strip(), v.strip()
                    if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')): v = v[1:-1]
                    os.environ.setdefault(k, v)
        except Exception: pass

def _pick_token(cli_token: str | None) -> str:
    if cli_token: return cli_token.strip()
    for k in ("DISCORD_BOT_TOKEN", "discord_bot_token", "DISCORD_TOKEN"):
        v = os.getenv(k, "").strip()
        if v: return v
    return ""

def _pick_channel_id(cli_channel: int | None) -> int | None:
    if cli_channel: return int(cli_channel)
    for k in ("QNA_CHANNEL_ID", "LEARNING_QNA_CHANNEL_ID"):
        v = (os.getenv(k) or "").strip()
        if v.isdigit(): return int(v)
    for p in ("data/config/overrides.render-free.json", "data/config/runtime_env.json"):
        try:
            with open(p, "r", encoding="utf-8") as fh:
                js = json.load(fh)
            for k in ("QNA_CHANNEL_ID", "LEARNING_QNA_CHANNEL_ID"):
                v = str(js.get(k, "")).strip()
                if v.isdigit(): return int(v)
        except Exception: pass
    return None

def _smoke_id(n: int = 6) -> str:
    import random, string
    return "".join(random.choice(string.hexdigits.lower()) for _ in range(n))

def _groq_probe():
    key = os.getenv("GROQ_API_KEY", "").strip()
    status = {"key": "MISSING", "https": "SKIP", "code": None, "ok": False}
    if key:
        status["key"] = "SET"
        try:
            req = urllib.request.Request("https://api.groq.com/openai/v1/models")
            req.add_header("Authorization", f"Bearer {key}")
            # Small timeout + default SSL context
            with urllib.request.urlopen(req, timeout=6) as resp:
                status["https"] = "OK"
                status["code"] = resp.getcode()
                status["ok"] = (resp.getcode() in (200, 401))  # 401 means reachable but bad key
        except Exception as e:
            status["https"] = f"FAIL: {e.__class__.__name__}"
            status["ok"] = False
    else:
        status["key"] = "MISSING"
    return status

async def amain():
    ap = argparse.ArgumentParser(description="QNA smoke (preflight)")
    ap.add_argument("--channel", type=int, default=0)
    ap.add_argument("--timeout", type=int, default=45)
    ap.add_argument("--provider", type=str, default="", help="Expected provider label (optional)")
    ap.add_argument("--token", type=str, default="")
    args = ap.parse_args()

    _load_local_env()

    # Preflight summary
    if args.provider.lower().startswith("groq"):
        st = _groq_probe()
        print(f"[GROQ] key={st['key']} https={st['https']} code={st['code']}", flush=True)

    token = _pick_token(args.token)
    if not token:
        print("[FAIL] Set DISCORD_BOT_TOKEN (or --token).", file=sys.stderr); sys.exit(2)

    channel_id = _pick_channel_id(args.channel if args.channel else None)
    if not channel_id:
        print("[FAIL] QNA channel id not provided (use --channel or set QNA_CHANNEL_ID).", file=sys.stderr); sys.exit(2)

    # Provider hints
    if args.provider:
        os.environ.setdefault("QNA_FORCE_PROVIDER", args.provider)
        os.environ.setdefault("QNA_PROVIDER_PRIORITY", args.provider)
        os.environ.setdefault("LLM_PROVIDER", args.provider)
        if args.provider.lower().startswith("groq"):
            os.environ.setdefault("GEMINI_FORCE_DISABLE", "1")
        if args.provider.lower().startswith("gemini"):
            os.environ.setdefault("GROQ_FORCE_DISABLE", "1")

    intents = discord.Intents.none()
    intents.guilds = True; intents.guild_messages = True; intents.messages = True; intents.message_content = False
    from discord.ext import commands
    bot = commands.Bot(command_prefix="!", intents=intents)

    os.environ.setdefault("QNA_CHANNEL_ID", str(channel_id))
    os.environ.setdefault("LEARNING_QNA_CHANNEL_ID", str(channel_id))
    os.environ.setdefault("QNA_RUNTIME_DEBUG", "1")
    os.environ.setdefault("QNA_AUTOPILOT", "0"); os.environ.setdefault("QNA_AUTOPILOT_ENABLE", "0")

    import importlib, importlib.util, sys
    from pathlib import Path
    def _ensure_repo_on_sys_path() -> Path:
        cwd = Path.cwd().resolve()
        cands = [cwd, *list(cwd.parents)[:4]]
        for base in cands:
            if (base / "satpambot").exists() or (base / "scripts").exists():
                p = str(base); 
                if p not in sys.path: sys.path.insert(0, p)
                return base
        if str(cwd) not in sys.path: sys.path.insert(0, str(cwd))
        return cwd
    _REPO_ROOT = _ensure_repo_on_sys_path()

    def _import_module_or_file(modname: str, filename: str):
        try:
            return importlib.import_module(modname)
        except ModuleNotFoundError:
            pass
        for root in [_REPO_ROOT, *_REPO_ROOT.parents]:
            for p in root.rglob(f"**/cogs/{filename}.py"):
                try:
                    mname = f"smoke_dynamic.{filename}"
                    spec = importlib.util.spec_from_file_location(mname, p)
                    if spec and spec.loader:
                        m = importlib.util.module_from_spec(spec)
                        sys.modules[mname] = m
                        spec.loader.exec_module(m)  # type: ignore
                        return m
                except Exception:
                    continue
        return None

    async def _safe_setup(mod, bot) -> bool:
        if not mod: return False
        setup = getattr(mod, "setup", None)
        if setup is None: return False
        res = setup(bot)
        if asyncio.iscoroutine(res): await res
        return True

    qna_mod = _import_module_or_file("satpambot.bot.modules.discord_bot.cogs.a24_qna_auto_answer_overlay","a24_qna_auto_answer_overlay")
    if not await _safe_setup(qna_mod, bot):
        print("[FAIL] cannot load a24_qna_auto_answer_overlay", file=sys.stderr); sys.exit(2)

    smoke_tag = f"smoke:{_smoke_id()}"
    got = {"provider": "", "title": ""}
    start = time.time()

    @bot.event
    async def on_ready():
        print(f"[READY] {bot.user} guilds={len(bot.guilds)}", flush=True)
        try:
            ch = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
        except Exception as e:
            print(f"[FAIL] cannot access channel {channel_id}: {e}", file=sys.stderr); await bot.close(); return
        emb = discord.Embed(title="Question by Leina", description="Sebutkan satu fakta singkat tentang kopi. Jawab ringkas (≤20 kata).")
        try: emb.set_footer(text=smoke_tag)
        except Exception: pass
        try:
            await ch.send(embed=emb); print(f"[CHANNEL] question sent {channel_id} ({smoke_tag})", flush=True)
        except Exception as e:
            print(f"[FAIL] send embed failed: {e}", file=sys.stderr); await bot.close()

    @bot.event
    async def on_message(message: discord.Message):
        if getattr(getattr(message, "channel", None), "id", None) != channel_id: return
        if not message.embeds: return
        e = message.embeds[0]; title = (getattr(e, "title", "") or "")
        if not title.lower().startswith("answer by"): return
        prov = title.split("Answer by", 1)[-1].strip() or "Provider"
        got["provider"], got["title"] = prov, title
        print(f"[CHANNEL] provider answer: {title}", flush=True)
        await bot.close()

    async def _waiter():
        last = -1
        while time.time() - start < args.timeout and not got["title"]:
            sec = int(time.time() - start)
            if sec != last:
                print(f"[WAIT] {sec}s...", flush=True)
                last = sec
            await asyncio.sleep(0.3)

    try:
        task = asyncio.create_task(bot.start(token, reconnect=False))
        await _waiter()
    except discord.LoginFailure:
        print("[FAIL] bad token", file=sys.stderr); sys.exit(2)
    except Exception as e:
        print(f"[FAIL] discord client error: {e}", file=sys.stderr); sys.exit(2)
    finally:
        try: await bot.close()
        except Exception: pass

    if not got["title"]:
        print("[TIMEOUT] no provider answer observed", file=sys.stderr); print("SMOKE_FAIL"); sys.exit(1)
    if args.provider and (args.provider.lower() not in got["provider"].lower()):
        print(f"[MISMATCH] expected ~ '{args.provider}', got '{got['provider']}'", file=sys.stderr); print("SMOKE_FAIL"); sys.exit(1)
    print(f"CHANNEL_OK provider={got['provider']}"); print("SMOKE_OK"); sys.exit(0)

if __name__ == "__main__":
    try: asyncio.run(amain())
    except KeyboardInterrupt: print("SMOKE_ABORT")
