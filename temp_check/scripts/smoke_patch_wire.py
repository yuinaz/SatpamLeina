import os, sys, types, importlib, re, asyncio
from pathlib import Path

# --- Auto-detect repo root (look upward for 'satpambot' directory) ---
SCRIPT = Path(__file__).resolve()
def _find_root(start: Path) -> Path:
    p = start
    for _ in range(8):
        if (p / "satpambot").is_dir():
            return p
        p = p.parent
    # fallback: current working dir
    return Path.cwd()

ROOT = _find_root(SCRIPT.parent)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- Stubs for discord / commands ---
discord_mod = types.ModuleType("discord")
class _Author:
    def __init__(self, bot=False, id=111): self.bot = bot; self.id = id
class _Channel:
    def __init__(self, id): self.id = id
    async def send(self, *a, **k): Smoke.outbox.append(("send", a, k))
class Message:
    def __init__(self, *, author, guild=True, channel=None, embeds=None, id=1):
        self.author = author
        self.guild = guild
        self.channel = channel or _Channel(0)
        self.embeds = embeds or []
        self.id = id
    async def reply(self, *a, **k): Smoke.outbox.append(("reply", a, k))
class Embed:
    def __init__(self, title=None): self.title = title; self.description = None; self.fields = []
discord_mod.Message = Message
discord_mod.Embed = Embed
discord_mod.ext = types.ModuleType("ext")
commands_mod = types.ModuleType("discord.ext.commands")
class Cog:
    @classmethod
    def listener(cls, *a, **k):
        def deco(fn): return fn
        return deco
class Bot:
    def __init__(self): self._events = []
    def dispatch(self, evt, *args): self._events.append((evt,)+args)
commands_mod.Cog = Cog
commands_mod.Bot = Bot
discord_mod.ext.commands = commands_mod

sys.modules["discord"] = discord_mod
sys.modules["discord.ext"] = discord_mod.ext
sys.modules["discord.ext.commands"] = commands_mod

# ---- Import user's smoke_utils ----
from importlib.machinery import SourceFileLoader
import os as _os
_SU_CANDIDATES = [
    _os.path.join(_os.getcwd(), "smoke_utils.py"),
    str(ROOT / "smoke_utils.py"),
    str(SCRIPT.parent / "smoke_utils.py"),
    "/mnt/data/smoke_utils.py",
]
SU = None
for _p in _SU_CANDIDATES:
    if _os.path.exists(_p):
        SU = SourceFileLoader("smoke_utils", _p).load_module()
        break
if SU is None:
    raise RuntimeError("smoke_utils.py not found; place it next to this smoke script or at repo root")

# Make a bot with dispatch capture
class BotCapture(SU.DummyBot):
    def __init__(self):
        super().__init__()
        self._events = []
    def dispatch(self, evt, *args):
        self._events.append((evt,)+args)

class Smoke:
    outbox = []

async def test_upstash_patch():
    # statically validate that .get_raw is used (not .cmd)
    p = ROOT / "satpambot/bot/modules/discord_bot/cogs/a08_passive_total_offset_overlay.py"
    src = p.read_text(encoding="utf-8")
    assert ".cmd(" not in src, "Found deprecated UpstashClient.cmd(...)"
    assert "get_raw(" in src, "Expected UpstashClient.get_raw(...)"
    return True

async def test_shadow_observer():
    mod = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.shadow_learn_observer")
    Bot = BotCapture
    bot = Bot()
    cog = mod.ShadowLearnObserver(bot)
    ch = _Channel(999)
    msg = Message(author=_Author(bot=False, id=12345), guild=True, channel=ch, id=1001)
    await cog.on_message(msg)
    ok = False
    for e in bot._events:
        evt = e[0]
        if evt in ("xp_add","satpam_xp","xp_award") and e[2] == 15:
            ok = True; break
    assert ok, f"No +15 XP event emitted, got {bot._events}"
    return True

async def test_qna_auto():
    os.environ["QNA_ENABLE"] = "1"
    os.environ["QNA_CHANNEL_ID"] = "4242424242"
    mod = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.a24_qna_auto_answer_overlay")
    bot = BotCapture()
    cog = mod.QnaAutoAnswerOverlay(bot)
    async def fake_aask(q): return ("jawaban-uji", "Groq")
    cog.provider.aask = fake_aask
    emb = Embed(title="Question by Leina")
    emb.description = "Apa itu cache?"
    ch = _Channel(int(os.environ["QNA_CHANNEL_ID"]))
    msg = Message(author=_Author(bot=True), guild=True, channel=ch, embeds=[emb], id=2002)
    await cog.on_message(msg)
    assert Smoke.outbox, "QnA produced no reply/send"
    kind, args, kwargs = Smoke.outbox[-1]
    e = None
    for x in args:
        if isinstance(x, Embed): e = x; break
    if e is None:
        e = kwargs.get('embed') if isinstance(kwargs.get('embed', None), Embed) else None
    assert e is not None, "QnA did not send an Embed"
    assert (e.description or "").strip().lower().startswith("jawaban-uji"), "Answer text mismatch"
    return True

async def main():
    results = []
    for name, fn in [
        ("upstash_client_api", test_upstash_patch),
        ("shadow_learning_observer", test_shadow_observer),
        ("qna_auto_answer", test_qna_auto),
    ]:
        try:
            ok = await fn()
            results.append((name, "PASS" if ok else "FAIL"))
        except Exception as e:
            results.append((name, f"FAIL: {e}"))
    for n, r in results:
        print(f"[SMOKE] {n}: {r}")
    failed = [r for _, r in results if not r.startswith("PASS")]
    if failed:
        raise SystemExit(1)

if __name__ == "__main__":
    asyncio.run(main())
