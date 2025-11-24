from __future__ import annotations

from discord.ext import commands
import asyncio, logging, re, os, json, fnmatch, importlib, ast, time, traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import discord
from discord.ext import tasks
from satpambot.config.local_cfg import cfg, cfg_bool, cfg_int, cfg_list

log = logging.getLogger(__name__)

OWNER_ID = int(cfg("OWNER_USER_ID", 0) or 0)
LOG_CHANNEL_ID = int(cfg("LOG_CHANNEL_ID", 0) or 0)
THREAD_NAME = cfg("SELFHEAL_THREAD_NAME", "Self-Heal Log") or "Self-Heal Log"

ENABLED = cfg_bool("SELFHEAL_ENABLE", True)
COOLDOWN = int(cfg_int("SELFHEAL_COOLDOWN_SEC", 900) or 900)
MAX_EDIT_SIZE = int(cfg_int("SELFHEAL_MAX_EDIT_SIZE", 8000) or 8000)
MAX_FILES = int(cfg_int("SELFHEAL_MAX_FILES", 3) or 3)
WHITELIST = cfg_list("SELFHEAL_WHITELIST_GLOBS")
DENYLIST = cfg_list("SELFHEAL_DENYLIST_GLOBS")
APPROVAL_MODE = (cfg("SELFHEAL_APPROVAL_MODE", "auto") or "auto").lower()
AUTO_APPLY_LOW = cfg_bool("SELFHEAL_AUTO_APPLY_LOW_RISK", True)

# NOTE: this file is at satpambot/bot/modules/discord_bot/cogs/selfheal_autofix.py
# repo_root = parents[5]
ROOT = Path(__file__).resolve().parents[5]

DATA_DIR = ROOT / "data/selfheal"
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = DATA_DIR / "state.json"
THREAD_STATE_FILE = DATA_DIR / "thread_state.json"

def _load_json(p: Path) -> Dict[str, Any]:
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}
def _save_json(p: Path, st: Dict[str, Any]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")

def _load_state() -> Dict[str, Any]: return _load_json(STATE_FILE)
def _save_state(st: Dict[str, Any]) -> None: _save_json(STATE_FILE, st)

def _sig_from_exc_text(txt: str) -> str:
    m = re.search(r'File "([^"]+)", line (\d+), in ([^\n]+)', txt)
    key = (m.group(1), m.group(2), m.group(3)) if m else ("unknown", "0", "run")
    return "|".join(key)

def _is_allowed_path(path: Path) -> bool:
    rp = str(path).replace("\\","/")
    if any(fnmatch.fnmatch(rp, g) for g in DENYLIST): return False
    if any(fnmatch.fnmatch(rp, g) for g in WHITELIST): return True
    return False

def _module_name_for_path(p: Path) -> Optional[str]:
    try:
        rp = str(p.relative_to(ROOT)).replace(os.sep, "/")
        if rp.endswith(".py"): rp = rp[:-3]
        return rp.replace("/", ".")
    except Exception:
        return None

def parse_plan(text: str) -> Optional[Dict[str, Any]]:
    # try robust overlay if present
    try:
        mod = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.a06_selfheal_json_guard_overlay")
        if hasattr(mod, "parse_plan"): return getattr(mod, "parse_plan")(text)
    except Exception:
        pass
    # minimal fallback
    try:
        return json.loads(text)
    except Exception:
        s = re.sub(r"^```(?:json)?\s*","", str(text or "").strip(), flags=re.IGNORECASE)
        s = re.sub(r"```$","", s.strip())
        try: return json.loads(s)
        except Exception: return None

async def _groq_propose_patch(prompt: str) -> Optional[Dict[str, Any]]:
    try:
        gh = importlib.import_module("satpambot.ml.groq_helper")
        resp = await gh.chat(system="You are a careful code repair agent. Output STRICT JSON only.",
                             user=prompt, model=None, temperature=0.2)
        if not resp: return None
        return parse_plan(resp) or None
    except Exception as e:
        log.warning("[selfheal] groq propose failed: %s", e)
        return None

@dataclass
class Edit:
    path: str
    replace: Optional[str] = None
    find: Optional[str] = None
    mode: str = "auto"  # "full" | "auto"

def _validate_code_py(path: Path, src: str) -> Tuple[bool, str]:
    try:
        ast.parse(src)
        return True, "ast-ok"
    except Exception as e:
        return False, f"ast-fail: {e}"

def _apply_edits(edits: List[Edit]) -> Tuple[bool, str, List[Path]]:
    changed: List[Path] = []
    if len(edits) > MAX_FILES:
        return False, f"too many files in patch (>{MAX_FILES})", []
    for e in edits:
        if not e.path: return False, "missing path", []
        p = ROOT / e.path
        if not _is_allowed_path(p):
            return False, f"path not allowed: {e.path}", []
        old = p.read_text(encoding="utf-8") if p.exists() else ""
        if e.replace is None:
            return False, f"edit missing 'replace' for {e.path}", []
        new_src = e.replace if (e.mode=="full" or e.find is None) else (old.replace(e.find, e.replace, 1) if e.find in old else None)
        if new_src is None:
            return False, f"find string not found in {e.path}", []
        if len(new_src.encode("utf-8")) > MAX_EDIT_SIZE:
            return False, f"edit too large for {e.path}", []
        ok, reason = _validate_code_py(p, new_src) if p.suffix==".py" else (True, "skip-ast")
        if not ok: return False, reason, []
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(new_src, encoding="utf-8")
        changed.append(p)
    return True, "ok", changed

async def _reload_changed(bot: commands.Bot, files: List[Path]) -> Tuple[bool, str]:
    modules = set()
    for p in files:
        m = _module_name_for_path(p)
        if m: modules.add(m)
    for m in modules:
        try:
            if m in bot.extensions:
                await bot.reload_extension(m)
            else:
                importlib.invalidate_caches()
                importlib.import_module(m)
        except Exception as e:
            return False, f"reload failed {m}: {e}"
    return True, "reloaded"

# --- tidy embed posting with simple coalescing (fallback if overlay not loaded) ---
async def _ensure_log_thread(bot: commands.Bot) -> Tuple[Optional[discord.TextChannel], Optional[discord.Thread]]:
    ch = bot.get_channel(LOG_CHANNEL_ID) if LOG_CHANNEL_ID else None
    if not ch or not isinstance(ch, discord.TextChannel):
        return None, None
    st = _load_json(THREAD_STATE_FILE)
    th_id = int(st.get("thread_id", 0) or 0)
    th = None
    if th_id:
        th = bot.get_channel(th_id)
    if th is None:
        try:
            msg = await ch.send("🩹 Self-heal log thread init.")
            th = await msg.create_thread(name=THREAD_NAME)
            st["thread_id"] = th.id
            _save_json(THREAD_STATE_FILE, st)
        except Exception:
            th = None
    return ch, th

async def _post_embed(bot: commands.Bot, title: str, description: str, *, fields: Dict[str,str]|None=None, color: int=0x2b9dff):
    ch, th = await _ensure_log_thread(bot)
    if not ch and not th:
        return
    emb = discord.Embed(title=title, description=description, color=color)
    emb.set_footer(text="Self-heal")
    target = th or ch
    try:
        await target.send(embed=emb)
    except Exception:
        # fallback plain text
        await target.send(f"**{title}**\n{description}")

async def _post(bot: commands.Bot, content: str):
    # basic wrapper for overlay compatibility
    await _post_embed(bot, "Self-Heal", content)

class SelfHealAutoFix(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.enabled = ENABLED
        self.queue: asyncio.Queue[Tuple[str, str]] = asyncio.Queue()

    async def cog_load(self) -> None:
        # start worker when cog is fully loaded (safe for discord.py 2.x)
        if not self.enabled:
            log.info("[selfheal] disabled by config")
            return
        self.worker.start()

    def cog_unload(self):
        try: self.worker.cancel()
        except Exception: pass

    async def on_exception(self, source: str, exc_text: str):
        if not self.enabled: return
        sig = _sig_from_exc_text(exc_text)
        st = _load_state()
        last = st.get("cooldown", {}).get(sig, 0)
        now = int(time.time())
        if now - int(last) < COOLDOWN:
            return
        await self.queue.put((source, exc_text))
        st.setdefault("cooldown", {})[sig] = now
        _save_state(st)

    @tasks.loop(seconds=5.0)
    async def worker(self):
        if not self.enabled: return
        try:
            source, exc_text = await self.queue.get()
        except Exception:
            return
        try:
            await self._handle_event(source, exc_text)
        except Exception as e:
            log.warning("[selfheal] handler error: %s", e)

    @worker.before_loop
    async def _wait_ready(self):
        await self.bot.wait_until_ready()

    async def _handle_event(self, source: str, exc_text: str):
        prompt = f'''
Fix the following Python error by proposing a minimal safe patch.
Return STRICT JSON with keys: risk, summary, edits:[{{path, mode, find, replace}}]

Error:
{exc_text}

Allowed paths: {WHITELIST}
Disallowed: {DENYLIST}
Max files: {MAX_FILES}; Max edit size: {MAX_EDIT_SIZE} bytes.
        '''.strip()

        await _post(self.bot, f"🩹 Self-heal trigger from **{source}** → proposing fix...")
        plan = await _groq_propose_patch(prompt)
        if not plan or "edits" not in plan:
            await _post(self.bot, "⚠️ Groq didn't return a valid JSON plan. Skipping.")
            return
        risk = str(plan.get("risk","low")).lower()
        if APPROVAL_MODE == "off":
            await _post(self.bot, f"ℹ️ Plan ready (risk={risk}) but approval OFF.")
            return

        edits = [Edit(path=e.get("path",""), find=e.get("find"), replace=e.get("replace"), mode=e.get("mode","auto"))
                 for e in plan.get("edits", [])]
        ok, reason, changed = _apply_edits(edits)
        if not ok:
            await _post(self.bot, f"❌ Apply failed: {reason}")
            return

        ok2, reason2 = await _reload_changed(self.bot, changed)
        if not ok2:
            await _post(self.bot, f"❌ Reload failed: {reason2}")
            return

        await _post(self.bot, "✅ Self-heal applied (risk=%s): %s" % (
            risk, ", ".join(str(p.relative_to(ROOT)) for p in changed))
        )

    @commands.Cog.listener()
    async def on_error(self, event_method, *args, **kwargs):
        exc_text = traceback.format_exc()
        await self.on_exception(event_method, exc_text)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        exc_text = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        await self.on_exception("command_error", exc_text)
async def setup(bot):
    try:
        # idempotent guard
        if bot.get_cog('SelfHealAutoFix'):
            log.debug('[selfheal] already loaded; skipping')
            return
        await bot.add_cog(SelfHealAutoFix(bot))
        log.info('[selfheal] SelfHealAutoFix loaded')
    except Exception as e:
        log.warning('[selfheal] setup failed: %s', e)