#!/usr/bin/env python3
# scripts/smoke_guard_qna.py — smoketest:
# 1) ENV & overrides bebas phish/phash/reseed/ban
# 2) Semua cog bernama phish/phash/reseed/ban masuk DISABLED_COGS
# 3) QnA autolearn (Gemini→Groq) kirim Question+Answer (pakai LLM dummy, no network)

import os, sys, re, json, asyncio, types, importlib, pathlib

# Deteksi root repo (jalan dari root atau dari folder scripts/)
ROOT = pathlib.Path(__file__).resolve().parent
REPO_ROOT = ROOT if (ROOT / "satpambot").exists() else ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

GREEN = "\033[92m"; RED = "\033[91m"; YELLOW = "\033[93m"; RESET = "\033[0m"
def banner(t): print(f"\n{YELLOW}=== {t} ==={RESET}")
def fail(msg):  print(f"{RED}[FAIL]{RESET} {msg}"); return False
def ok(msg):    print(f"{GREEN}[OK]{RESET}  {msg}"); return True

def load_overrides_env():
    # Gabungkan overrides.render* kalau ada
    for p in [
        REPO_ROOT / "data" / "config" / "overrides.render-free.json",
        REPO_ROOT / "data" / "config" / "overrides.render.json",
    ]:
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8")).get("env", {})
            except Exception as e:
                print(f"{RED}[WARN]{RESET} overrides parse error ({p.name}): {e}")
    return {}

def scan_cogs():
    base = REPO_ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "cogs"
    out = []
    if base.exists():
        for p in base.rglob("*.py"):
            name = p.name.lower().replace(".py","")
            if any(t in name for t in ("phish","phash","reseed","ban")):
                out.append(name)
    return sorted(set(out))

def check_env_no_phish(env):
    bad = [k for k in env if re.search(r"(phish|phash|reseed|ban)", k, re.I)]
    if bad:
        for k in sorted(bad): print(" -", k)
        return fail("ENV masih mengandung kunci terkait phish/phash/reseed/ban")
    return ok("ENV bersih dari kunci phish/phash/reseed/ban")

def check_disabled_cogs(env, suspects):
    disabled = [x.strip() for x in (env.get("DISABLED_COGS","") or "").split(",") if x.strip()]
    disabled_set = set(disabled)
    miss = [s for s in suspects if s not in disabled_set]
    if miss:
        print("Cogs belum di-DISABLE:", ", ".join(miss))
        return fail("Masih ada cogs phish/phash/reseed/ban yang tidak masuk DISABLED_COGS")
    return ok(f"Semua {len(suspects)} cogs phish/phash/reseed/ban sudah di-DISABLE")

def ensure_discord_stubs():
    try:
        import discord  # noqa
        from discord.ext import commands, tasks  # noqa
        return
    except Exception:
        pass
    # Stubs minimal (supaya jalan tanpa discord.py)
    discord = types.ModuleType("discord"); sys.modules["discord"] = discord
    class Embed:
        def __init__(self, title=None, description=None):
            self.title=title; self.description=description; self.footer_text=None
        def set_footer(self, text=None): self.footer_text = text
    discord.Embed = Embed
    class TextChannel: pass
    class Thread: pass
    discord.TextChannel = TextChannel; discord.Thread = Thread
    ext = types.ModuleType("discord.ext"); sys.modules["discord.ext"] = ext
    commands = types.ModuleType("commands"); sys.modules["discord.ext.commands"] = commands
    tasks = types.ModuleType("tasks"); sys.modules["discord.ext.tasks"] = tasks
    class _Cog: pass
    commands.Cog = _Cog
    def loop(**kw):
        def deco(fn): return fn
        return deco
    tasks.loop = loop

class DummyChannel:
    def __init__(self): self.messages = []
    async def send(self, embed=None, reference=None):
        self.messages.append(("embed", getattr(embed, "title", None), getattr(embed, "description", None)))
        return types.SimpleNamespace(id=len(self.messages))

class DummyBot:
    def __init__(self, ch):
        self._ch = ch; self.cogs = {}
    def get_channel(self, _id): return self._ch
    async def wait_until_ready(self): return None
    def remove_cog(self, name): self.cogs.pop(name, None)

async def run_qna_one_round(fake_answer="SMOKE_ANSWER"):
    ensure_discord_stubs()
    modname = "satpambot.bot.modules.discord_bot.cogs.neuro_autolearn_moderated_v2"
    try:
        cogmod = importlib.import_module(modname)
    except Exception as e:
        return fail(f"Import cog gagal: {e}")
    ch = DummyChannel()
    bot = DummyBot(ch)
    cog = cogmod.NeuroAutolearnModeratedV2(bot)
    # LLM dummy (no-network)
    class _FakeLLM:
        async def answer(self, prompt, system):
            return fake_answer
    cog._llm = _FakeLLM()
    cog._topics = ["Apa manfaat belajar konsisten setiap hari?"]
    try:
        await cog._one_round()
    except Exception as e:
        return fail(f"_one_round error: {e}")
    titles = [t for (_,t,_) in ch.messages]
    if titles.count("Question by Leina")>=1 and titles.count("Answer by Leina")>=1:
        return ok("QnA autolearn menghasilkan Question+Answer dalam satu putaran (no-network)")
    else:
        print("Terkirim:", ch.messages)
        return fail("QnA tidak mengirim Question+Answer seperti yang diharapkan")

def main():
    print()
    print("Repo root:", REPO_ROOT)
    banner("Memuat ENV (gabungan proses + overrides.render*)")
    env = dict(os.environ); env.update(load_overrides_env())
    banner("Cek ENV bebas phish/phash/reseed/ban")
    ok1 = check_env_no_phish(env)
    banner("Cek cogs berisiko (phish/phash/reseed/ban)")
    suspects = scan_cogs()
    print("Ditemukan:", len(suspects), "cogs")
    ok2 = check_disabled_cogs(env, suspects) if suspects else ok("Tidak ada cogs berisiko ditemukan")
    banner("QnA Autolearn — smoke tanpa jaringan (Gemini/Groq wiring)")
    ok3 = asyncio.run(run_qna_one_round())
    banner("Rangkuman")
    all_ok = ok1 and ok2 and ok3
    if all_ok:
        print(f"{GREEN}ALL GREEN{RESET} — Guard OFF (phish/phash/ban/reseed) & QnA autolearn siap.")
        sys.exit(0)
    else:
        print(f"{RED}SOME CHECKS FAILED{RESET} — cek log di atas.")
        sys.exit(1)

if __name__ == "__main__":
    main()
