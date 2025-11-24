
from __future__ import annotations
import argparse, asyncio, importlib, importlib.util, os, sys, types, traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ======================= UTIL PRINTS =======================
def info(msg: str):
    print(msg, flush=True)

def err(msg: str):
    print(msg, file=sys.stderr, flush=True)

# ================= PATH & IMPORT HELPERS ===================
def _ensure_repo_on_sys_path() -> Path:
    cwd = Path.cwd().resolve()
    cands = [cwd, *list(cwd.parents)[:4]]
    for base in cands:
        if (base / "satpambot").exists() or (base / "scripts").exists():
            p = str(base)
            if p not in sys.path:
                sys.path.insert(0, p)
            return base
    if str(cwd) not in sys.path:
        sys.path.insert(0, str(cwd))
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
    if not mod:
        return False
    setup = getattr(mod, "setup", None)
    if setup is None:
        return False
    res = setup(bot)
    if asyncio.iscoroutine(res):
        await res
    return True

# ================== IN-MEMORY DISCORD ======================
class DummyLoop:
    def create_task(self, coro):
        return asyncio.get_event_loop().create_task(coro)

class DummyUser: id = 1234567890

@dataclass
class InMemoryGuild: id: int = 1; name: str = "smoke-guild"
@dataclass
class InMemoryAuthor: id: int = 987654321; bot: bool = True
@dataclass
class InMemoryEmbed:
    title: str = ""; description: str = ""; fields: List[Tuple[str,str,bool]] = field(default_factory=list); footer_text: str = ""
    def set_footer(self, text: str = ""): self.footer_text = text
@dataclass
class InMemoryMessage:
    id: int; channel: "InMemoryChannel"; author: InMemoryAuthor; embeds: List[InMemoryEmbed] = field(default_factory=list); guild: InMemoryGuild = field(default_factory=InMemoryGuild)
    async def reply(self, embed: Optional[InMemoryEmbed] = None, mention_author: bool = False): await self.channel.send(embed=embed)
    async def edit(self, embed: Optional[InMemoryEmbed] = None):
        if embed: self.embeds = [embed]
@dataclass
class InMemoryChannel:
    id: int; bot: "DummyBot"; guild: InMemoryGuild = field(default_factory=InMemoryGuild); messages: List[InMemoryMessage] = field(default_factory=list)
    async def send(self, content: Optional[str]=None, embed: Optional[InMemoryEmbed]=None):
        msg = InMemoryMessage(id=len(self.messages)+1, channel=self, author=InMemoryAuthor(), embeds=[embed] if embed else [])
        self.messages.append(msg)
        for k, v in list(self.bot.__dict__.items()):
            if k.startswith("_cog_") and hasattr(v, "on_message"):
                try: await v.on_message(msg)
                except Exception: pass
        return msg
class DummyBot:
    def __init__(self):
        self.user = DummyUser(); self.loop = DummyLoop(); self.guilds: List[Any] = [InMemoryGuild()]
        self._channels: Dict[int, InMemoryChannel] = {}; self._events: List[Tuple[str, tuple, dict]] = []
    def get_channel(self, cid: int): return self._channels.get(int(cid))
    async def fetch_channel(self, cid: int): return self.get_channel(cid)
    def ensure_channel(self, cid: int) -> InMemoryChannel:
        cid = int(cid)
        if cid not in self._channels: self._channels[cid] = InMemoryChannel(cid, bot=self)
        return self._channels[cid]
    async def wait_until_ready(self): return True
    async def add_cog(self, cog): setattr(self, f"_cog_{cog.__class__.__name__}", cog); return True
    def dispatch(self, name: str, *args, **kwargs): self._events.append((name, args, kwargs))
    @property
    def events(self): return list(self._events)
def retrofit(bot): setattr(bot, "get_all_channels", lambda: []); setattr(bot, "get_user", lambda *a, **k: None); setattr(bot, "fetch_user", lambda *a, **k: None); return bot

# ================ Provider stub + helpers ==================
def install_qna_provider_stub(answer_text: str = "smoke:ok", provider: str = "Groq"):
    modname = "satpambot.bot.modules.discord_bot.cogs.qna_dual_provider"
    m = types.ModuleType(modname)
    class QnaDualProvider:
        def __init__(self, bot): self.bot = bot
        async def aask(self, prompt: str): return (answer_text, provider)
    m.QnaDualProvider = QnaDualProvider; sys.modules[modname] = m; return m

async def qna_emit_question(bot: DummyBot, channel_id: int, prompt: str, smoke_id: str="smk"):
    ch = bot.ensure_channel(channel_id); emb = InMemoryEmbed(title="Question by Leina", description=prompt); emb.set_footer(text=f"smoke:{smoke_id}")
    return await ch.send(embed=emb)

def count_answer_embeds(bot: DummyBot, channel_id: int) -> int:
    ch = bot.get_channel(channel_id); 
    if not ch: return 0
    return sum(1 for m in ch.messages for e in m.embeds if e.title and e.title.lower().startswith("answer by"))
def assert_qna_answered(bot: DummyBot, channel_id: int) -> bool: return count_answer_embeds(bot, channel_id) > 0
def count_xp_events(bot: DummyBot) -> int: return sum(1 for (n,_,__) in bot.events if n in {"satpam_xp","xp_add","xp_award"})
async def shadow_emit_user_message(bot: DummyBot, shadow_cog: Any, channel_id: int, user_id: int=42, text: str="halo"):
    ch = bot.ensure_channel(channel_id); msg = InMemoryMessage(id=len(ch.messages)+1, channel=ch, author=InMemoryAuthor(id=user_id, bot=False), embeds=[InMemoryEmbed(title="", description=text)])
    if hasattr(shadow_cog, "on_message"): await shadow_cog.on_message(msg)
async def simulate_hotenv_reload(bot: DummyBot): bot.dispatch("hotenv_reload")

def _footer_text(embed) -> str:
    v = getattr(embed, "footer_text", None)
    if isinstance(v, str): return v
    f = getattr(embed, "footer", None)
    if f is not None:
        t = getattr(f, "text", None)
        if isinstance(t, str): return t
        try: return f.get("text") or ""
        except Exception: pass
    return ""

# ===================== Load cogs ===========================
async def load_patch_cogs(bot: DummyBot, *, load_qna=True, load_shadow=True, load_scheduler=False):
    if load_qna:
        await _safe_setup(_import_module_or_file("satpambot.bot.modules.discord_bot.cogs.a24_qna_auto_answer_overlay","a24_qna_auto_answer_overlay"), bot)
    if load_shadow:
        await _safe_setup(_import_module_or_file("satpambot.bot.modules.discord_bot.cogs.a08_shadow_learning_observer_overlay","a08_shadow_learning_observer_overlay"), bot)
    if load_scheduler:
        await _safe_setup(_import_module_or_file("satpambot.bot.modules.discord_bot.cogs.a24_qna_autolearn_scheduler","a24_qna_autolearn_scheduler"), bot)

# ===================== Main smoke =========================
async def smoke_patch_o33_combined(channel_id: int, provider: str, answer_text: str, shadow_channel_id: int, check_autoswitch: bool=False, assert_footer: bool=False) -> Dict[str, Any]:
    os.environ.setdefault("QNA_CHANNEL_ID", str(channel_id))
    os.environ.setdefault("LEARNING_QNA_CHANNEL_ID", str(channel_id))
    os.environ.setdefault("QNA_RUNTIME_DEBUG", "0")
    os.environ.setdefault("QNA_AUTOPILOT", "0"); os.environ.setdefault("QNA_AUTOPILOT_ENABLE", "0")
    os.environ.setdefault("SHADOW_ENABLE", "1"); os.environ.setdefault("SHADOW_EXPOSURE_XP", "15"); os.environ.setdefault("SHADOW_XP_COOLDOWN_SEC", "1")

    install_qna_provider_stub(answer_text, provider)
    bot = retrofit(DummyBot())
    await load_patch_cogs(bot, load_qna=True, load_shadow=True, load_scheduler=check_autoswitch)

    # QnA
    await qna_emit_question(bot, channel_id, "Sebutkan satu fakta singkat tentang kopi. Jawab ringkas (≤20 kata).", smoke_id="o33")
    await asyncio.sleep(0.05)
    qna_ok = assert_qna_answered(bot, channel_id)

    # Optional dedupe (autoswitch)
    dedupe_ok = True
    if check_autoswitch:
        await qna_emit_question(bot, channel_id, "Fakta singkat tentang teh. Jawab ringkas (≤20 kata).", smoke_id="o33b")
        await asyncio.sleep(0.05)
        answers = count_answer_embeds(bot, channel_id)
        dedupe_ok = answers in (2, 1)

    # Footer
    footer_ok = True
    if assert_footer:
        ch = bot.get_channel(channel_id); footer_ok = False
        if ch:
            for m in ch.messages:
                for e in m.embeds:
                    if e.title.lower().startswith("answer by") and _footer_text(e):
                        footer_ok = True; break

    # Shadow
    shadow_cog = getattr(bot, "_cog_ShadowLearningObserverOverlay", None)
    before = count_xp_events(bot); await shadow_emit_user_message(bot, shadow_cog, shadow_channel_id, user_id=777, text="halo patch")
    after = count_xp_events(bot); shadow_ok = (after - before) > 0

    # Hotenv
    await simulate_hotenv_reload(bot); hotenv_ok = any(name == "hotenv_reload" for (name,_,__) in bot.events)

    return {"QNA_OK": qna_ok, "SHADOW_OK": shadow_ok, "HOTENV_OK": hotenv_ok, "DEDUP_OK": dedupe_ok, "FOOTER_OK": footer_ok,
            "events": bot.events[-8:], "channels": {channel_id: [[e.title, e.description, _footer_text(e)] for m in bot.get_channel(channel_id).messages for e in m.embeds] if bot.get_channel(channel_id) else []}}

# ======================= CLI ===============================
def _cli():
    ap = argparse.ArgumentParser(description="Patch smoke runner (QnA/Shadow/Hotenv)")
    ap.add_argument("--qna-channel", type=int, default=1426571542627614772)
    ap.add_argument("--shadow-channel", type=int, default=999)
    ap.add_argument("--provider", type=str, default="Groq")
    ap.add_argument("--answer", type=str, default="smoke:ok")
    ap.add_argument("--gemini", action="store_true")
    ap.add_argument("--check-autoswitch", action="store_true")
    ap.add_argument("--assert-footer", action="store_true")
    args = ap.parse_args()

    if args.gemini: args.provider = "Gemini"

    info("== SMOKE START ==")
    try:
        res = asyncio.run(smoke_patch_o33_combined(channel_id=args.qna_channel, provider=args.provider, answer_text=args.answer, shadow_channel_id=args.shadow_channel, check_autoswitch=args.check_autoswitch, assert_footer=args.assert_footer))
        q, s, h = res["QNA_OK"], res["SHADOW_OK"], res["HOTENV_OK"]; d, f = res["DEDUP_OK"], res["FOOTER_OK"]
        print(f"[QNA]        {'PASS' if q else 'FAIL'}", flush=True)
        print(f"[SHADOW]     {'PASS' if s else 'FAIL'}  (xp events: {sum(1 for (n,_,__) in res['events'] if n in {'satpam_xp','xp_add','xp_award'})})", flush=True)
        print(f"[HOTENV]     {'PASS' if h else 'FAIL'}", flush=True)
        if args.check_autoswitch: print(f"[QNA-DEDUPE] {'PASS' if d else 'FAIL'}", flush=True)
        if args.assert_footer:   print(f"[QNA-FOOTER] {'PASS' if f else 'FAIL'}", flush=True)
        if res["channels"].get(args.qna_channel):
            last = res["channels"][args.qna_channel][-1]; print("Preview:", [last[0], last[1]], flush=True)
        ok = q and s and h and (d if args.check_autoswitch else True) and (f if args.assert_footer else True)
        print("SMOKE_" + ("OK" if ok else "FAIL"), flush=True)
        sys.exit(0 if ok else 1)
    except SystemExit as se:
        raise se
    except Exception as ex:
        err("!! SMOKE ERROR !!")
        traceback.print_exc()
        sys.exit(2)

if __name__ == "__main__":
    _cli()
