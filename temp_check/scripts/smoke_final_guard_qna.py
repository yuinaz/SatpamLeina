
#!/usr/bin/env python3
# scripts/smoke_final_guard_qna.py (FINAL FIX)
import os, sys, json, asyncio, types, importlib, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
REPO_ROOT = ROOT if (ROOT / "satpambot").exists() else ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

GREEN="\033[92m"; RED="\033[91m"; YELLOW="\033[93m"; RESET="\033[0m"
def ok(msg):   print(f"{GREEN}[OK]{RESET}  {msg}"); return True
def warn(msg): print(f"{YELLOW}[WARN]{RESET} {msg}"); return True
def fail(msg): print(f"{RED}[FAIL]{RESET} {msg}"); return False
def banner(t): print(f"\n{YELLOW}=== {t} ==={RESET}")

QNA_COG_MOD = "satpambot.bot.modules.discord_bot.cogs.neuro_autolearn_moderated_v2"

def load_overrides_env():
    for p in [REPO_ROOT / "data" / "config" / "overrides.render-free.json",
              REPO_ROOT / "data" / "config" / "overrides.render.json"]:
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8")).get("env", {})
            except Exception:
                pass
    return {}

def ensure_discord_stubs():
    try:
        import discord
        from discord.ext import commands, tasks
        return
    except Exception:
        pass
    discord = types.ModuleType("discord"); sys.modules["discord"] = discord
    class Embed:
        def __init__(self, title=None, description=None):
            self.title=title; self.description=description; self.footer_text=None
        def set_footer(self, text=None): self.footer_text=text
    discord.Embed = Embed
    class TextChannel: pass
    class Thread: pass
    discord.TextChannel=TextChannel; discord.Thread=Thread
    ext = types.ModuleType("discord.ext"); sys.modules["discord.ext"] = ext
    commands = types.ModuleType("commands"); sys.modules["discord.ext.commands"] = commands
    tasks = types.ModuleType("tasks"); sys.modules["discord.ext.tasks"] = tasks
    class _Cog: pass
    commands.Cog = _Cog
    def loop(**kw):
        def deco(fn): return fn
        return deco
    tasks.loop = loop

class DummyBot:
    def __init__(self, ch): self._ch=ch; self.cogs={}
    def get_channel(self, _id): return self._ch  # always return our dummy channel
    async def wait_until_ready(self): return None
    def remove_cog(self, name): self.cogs.pop(name, None)

def check_env_min(env):
    ok_all = True
    ok_all &= ok("QNA_ENABLE=1") if env.get("QNA_ENABLE")=="1" else fail("QNA_ENABLE harus = 1")
    ok_all &= ok("QNA_AUTOPILOT=0") if env.get("QNA_AUTOPILOT")=="0" else fail("QNA_AUTOPILOT harus = 0")
    lp = (env.get("LLM_PROVIDER_ORDER","") or "").lower()
    qp = (env.get("QNA_PROVIDER_ORDER","") or "").lower()
    if not (lp.startswith("gemini") and "groq" in lp): ok_all &= fail("LLM_PROVIDER_ORDER sebaiknya 'gemini,groq'")
    else: ok_all &= ok(f"LLM_PROVIDER_ORDER={env.get('LLM_PROVIDER_ORDER')}")
    if not (qp.startswith("gemini") and "groq" in qp): ok_all &= fail("QNA_PROVIDER_ORDER sebaiknya 'gemini,groq'")
    else: ok_all &= ok(f"QNA_PROVIDER_ORDER={env.get('QNA_PROVIDER_ORDER')}")
    for k in ("OPENAI_BASE_URL","GROQ_BASE_URL"):
        v = env.get(k,"")
        if not v: warn(f"{k} kosong (boleh, fallback ke https://api.groq.com)")
        elif v.rstrip("/").endswith("/openai/v1"): ok_all &= fail(f"{k} JANGAN pakai '/openai/v1' → set ke 'https://api.groq.com'")
        elif v.startswith("https://api.groq.com"): ok_all &= ok(f"{k} OK: {v}")
        else: warn(f"{k} = {v} (pastikan kompatibel OpenAI-like)")
    return ok_all

async def check_qna_autolearn_round():
    ensure_discord_stubs()
    import discord, importlib
    try:
        cogmod = importlib.import_module(QNA_COG_MOD)
    except Exception as e:
        return fail(f"Import QnA cog gagal: {e}")
    # Define DummyChannel *after* discord stubs exist so isinstance(..., TextChannel) is True
    class DummyChannel(discord.TextChannel):
        def __init__(self): self.messages=[]
        async def send(self, embed=None, reference=None):
            self.messages.append(("embed", getattr(embed,"title",None), getattr(embed,"description",None)))
            return types.SimpleNamespace(id=len(self.messages))
    ch = DummyChannel()
    bot = DummyBot(ch)
    cog = cogmod.NeuroAutolearnModeratedV2(bot)
    # Force channel id so _get_qna_channel() picks our DummyChannel via bot.get_channel()
    cog.private_ch_id = 1
    cog.enable = True
    print(f"[info] test QNA_CHANNEL_ID set to {cog.private_ch_id}, name={cog.private_ch_name}")
    class _FakeLLM:
        async def answer(self, prompt, system): return "SMOKE_ANSWER"
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
    print("Repo root:", REPO_ROOT)
    env = dict(os.environ); env.update(load_overrides_env())
    banner("ENV minimal")
    ok_env = check_env_min(env)
    banner("QnA Autolearn — 1 putaran (no-network)")
    ok_qna = asyncio.run(check_qna_autolearn_round())
    banner("Rangkuman")
    if ok_env and ok_qna:
        print(f"{GREEN}ALL GREEN{RESET} — QnA autolearn siap (smoketest).")
        sys.exit(0)
    else:
        print(f"{RED}SOME CHECKS FAILED{RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()
