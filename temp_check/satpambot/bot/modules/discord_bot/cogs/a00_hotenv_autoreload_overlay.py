
from __future__ import annotations
import asyncio, os, time, json, logging, hashlib, re
from typing import Any, Dict, List, Optional, Tuple
try:
    from discord.ext import commands
except Exception as _e:
    commands = None  # type: ignore
    _IMPORT_ERR = _e
else:
    _IMPORT_ERR = None
log = logging.getLogger(__name__)
ENABLE   = os.getenv("HOTENV_ENABLE", "1") == "1"
INTERVAL = int(os.getenv("HOTENV_INTERVAL_SEC", "5"))
DEBOUNCE_MS = int(os.getenv("HOTENV_DEBOUNCE_MS", "800"))
MODE = (os.getenv("HOTENV_MODE", "category") or "category").lower()  # category | auto | allowlist
PREFIX = os.getenv("HOTENV_PREFIX", "satpambot.bot.modules.discord_bot.cogs.")
WATCH_FILES = [p.strip() for p in os.getenv("HOTENV_WATCH_FILES","data/config/overrides.render-free.json").split(",") if p.strip()]
RELOAD_EXTS = [m.strip() for m in os.getenv("HOTENV_RELOAD_EXTS","").split(",") if m.strip()]
EXCLUDE = [m.strip() for m in os.getenv("HOTENV_EXCLUDE","satpambot.bot.modules.discord_bot.cogs.a00_hotenv_autoreload_overlay").split(",") if m.strip()]
BROADCAST = os.getenv("HOTENV_BROADCAST_EVENT", "1") == "1"
OVERRIDES_PATH = os.getenv("CONFIG_OVERRIDES_PATH", "data/config/overrides.render-free.json")
def _sha1_bytes(b: bytes) -> str:
    h = hashlib.sha1(); h.update(b); return h.hexdigest()
def _json_load(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}
def _merge_env_from_json_env(js: Dict[str, Any]) -> int:
    cnt = 0
    env = js.get("env")
    if isinstance(env, dict):
        for k, v in env.items():
            if isinstance(k, str) and k.strip().startswith("-"):  # dashed headers
                continue
            if v is None: continue
            sv = str(v)
            if os.environ.get(k) != sv:
                os.environ[k] = sv
                cnt += 1
    return cnt
def _parse_sections_from_env_map(env: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    sections: List[Tuple[str, Dict[str, Any]]] = []
    cur_title = "UNSECTIONED"; cur_map: Dict[str, Any] = {}
    header_rx = re.compile(r'^\s*-{6,}\s*(.*?)\s*-{6,}\s*$')
    for k, v in env.items():
        if isinstance(k, str):
            m = header_rx.match(k)
            if m:
                if cur_map:
                    sections.append((cur_title, cur_map))
                cur_title = (m.group(1) or "").strip()
                cur_map = {}
                continue
        cur_map[k] = v
    if cur_map: sections.append((cur_title, cur_map))
    return sections
class HotEnvAutoReloadOverlay(commands.Cog):  # type: ignore[misc]
    def __init__(self, bot: Any):
        self.bot = bot
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()
        self._file_state: Dict[str, Dict[str, Any]] = {}
        self._section_hash: Dict[str, str] = {}
        self._last_reload_ts = 0.0
        try:
            raw = os.getenv("HOTENV_CATEGORY_MAP_JSON", "").strip()
            self._catmap: Dict[str, List[str]] = json.loads(raw) if raw else {}
        except Exception:
            self._catmap = {}
    async def cog_load(self):
        if not ENABLE:
            log.info("[hotenv] disabled"); return
        for p in WATCH_FILES:
            self._probe_file(p, first=True)
        self._refresh_section_hash(first=True)
        self._task = self.bot.loop.create_task(self._runner(), name="hotenv_autoreload_v3")
        log.info("[hotenv] v3 watching=%s | interval=%ss | mode=%s | prefix=%s", WATCH_FILES, INTERVAL, MODE, PREFIX)
    async def cog_unload(self):
        if self._task and not self._task.done():
            self._stop.set(); self._task.cancel()
            try: await self._task
            except asyncio.CancelledError: pass
            log.info("[hotenv] stopped")
    def _probe_file(self, path: str, first: bool=False) -> bool:
        try:
            st = os.stat(path)
        except FileNotFoundError:
            prev = self._file_state.get(path)
            if prev is not None:
                self._file_state[path] = {"mtime": None, "sha1": None}
                return True and not first
            self._file_state[path] = {"mtime": None, "sha1": None}; return False
        mtime = int(st.st_mtime)
        try:
            with open(path, "rb") as f: sha = _sha1_bytes(f.read())
        except Exception: sha = ""
        prev = self._file_state.get(path)
        if not prev:
            self._file_state[path] = {"mtime": mtime, "sha1": sha}; return False
        if prev["mtime"] != mtime or prev["sha1"] != sha:
            self._file_state[path] = {"mtime": mtime, "sha1": sha}; return True
        return False
    def _refresh_section_hash(self, first: bool=False) -> List[str]:
        try:
            js = _json_load(OVERRIDES_PATH); env = js.get("env") or {}; sections = _parse_sections_from_env_map(env)
        except Exception as e:
            log.warning("[hotenv] parse overrides failed: %r", e); return []
        changed: List[str] = []
        for title, kv in sections:
            items = [f"{k}={kv[k]}" for k in kv.keys() if not (isinstance(k,str) and k.strip().startswith("-"))]
            blob = ("\n".join(items)).encode("utf-8", "ignore"); h = _sha1_bytes(blob)
            prev = self._section_hash.get(title)
            if prev is None:
                self._section_hash[title] = h; continue
            if prev != h:
                self._section_hash[title] = h; changed.append(title)
        return changed
    @commands.command(name="hotenv")  # type: ignore[attr-defined]
    @commands.is_owner()              # type: ignore[attr-defined]
    async def hotenv_cmd(self, ctx: Any, sub: str="status", *args: str):
        sub = (sub or "status").lower()
        if sub == "status":
            await ctx.reply(self._status_text()); return
        if sub == "reload":
            await self._apply_and_reload(WATCH_FILES); await ctx.reply("[hotenv] reloaded"); return
        if sub == "mode" and args:
            global MODE; MODE = args[0].lower(); await ctx.reply(f"[hotenv] mode -> {MODE}"); return
        if sub == "prefix" and args:
            global PREFIX; PREFIX = args[0]; await ctx.reply(f"[hotenv] prefix -> {PREFIX}"); return
        if sub == "map":
            await ctx.reply(self._map_text()); return
        if sub == "mapset" and len(args) >= 2:
            sec = args[0]; mods = ",".join(args[1:]); self._set_map(sec, mods)
            await ctx.reply(f"[hotenv] map[{sec}] set -> {mods}"); return
        await ctx.reply("usage: !hotenv [status|reload|mode <category|auto|allowlist>|prefix <pkg>|map|mapset <section> <mod,...>]")
    def _map_text(self) -> str:
        lines = ["**HotEnv Category Map**"]
        for sec, mods in sorted(self._catmap.items()):
            if not mods: lines.append(f"- {sec}: (none)")
            else:
                for i,m in enumerate(mods): lines.append(f"- {sec}[{i+1}]: {m}")
        return "\n".join(lines)
    def _set_map(self, sec: str, mods_csv: str):
        mods = [m.strip() for m in mods_csv.split(",") if m.strip()]; self._catmap[sec] = mods
        os.environ["HOTENV_CATEGORY_MAP_JSON"] = json.dumps(self._catmap, separators=(",",":"))
    def _status_text(self) -> str:
        lines = ["**HotEnv Status (v3)**",
                 f"Enable: {ENABLE}  Interval: {INTERVAL}s  Debounce: {DEBOUNCE_MS}ms",
                 f"Mode: {MODE}  Prefix: {PREFIX}", "Watch files:"] + [f"- {p}" for p in WATCH_FILES]
        if MODE == "allowlist":
            lines += ["Reload (allowlist):"] + [f"- {m}" for m in RELOAD_EXTS]
        elif MODE == "auto":
            lines += ["Reload (auto by prefix):", f"- {PREFIX}*"]
        else:
            lines += ["Reload (category-aware)"]
        lines += ["Exclude:"] + [f"- {m}" for m in EXCLUDE]
        return "\n".join(lines)
    async def _runner(self):
        await asyncio.sleep(2)
        while not self._stop.is_set():
            changed_files = []
            for p in WATCH_FILES:
                try:
                    if self._probe_file(p):
                        logging.warning("[hotenv] change detected: %s", p); changed_files.append(p)
                except Exception:
                    logging.exception("[hotenv] probe error: %s", p)
            if changed_files:
                if (time.time() - self._last_reload_ts) * 1000.0 < DEBOUNCE_MS:
                    await asyncio.sleep(DEBOUNCE_MS / 1000.0)
                try:
                    await self._apply_and_reload(changed_files); self._last_reload_ts = time.time()
                except Exception:
                    logging.exception("[hotenv] reload error")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=INTERVAL)
            except asyncio.TimeoutError:
                pass
    async def _apply_and_reload(self, changed_files: List[str]):
        # Merge ENV from json
        changed_env = 0
        for p in WATCH_FILES:
            if p.endswith(".json"):
                js = _json_load(p); changed_env += _merge_env_from_json_env(js)
        # Merge from .env
        if any(p.endswith(".env") or p == ".env" for p in WATCH_FILES):
            try:
                with open(".env", "r", encoding="utf-8") as f:
                    for raw in f:
                        line = raw.strip()
                        if not line or line.startswith("#") or "=" not in line: continue
                        k, v = line.split("=", 1); k = k.strip(); v = v.strip()
                        if v.startswith(("'", '"')) and v.endswith(("'", '"')): v = v[1:-1]
                        if os.environ.get(k) != v: os.environ[k] = v; changed_env += 1
            except Exception: pass
        logging.warning("[hotenv] env merged: %s changes", changed_env)
        # targets
        targets: List[str] = []
        if MODE == "auto":
            try:
                targets = [m for m in list(getattr(self.bot, "extensions", {}).keys()) if m.startswith(PREFIX)]
            except Exception: targets = []
        elif MODE == "allowlist":
            targets = list(RELOAD_EXTS)
        else:
            sec_changed = self._refresh_section_hash(first=False) if OVERRIDES_PATH in changed_files else []
            if not sec_changed and any(p.endswith(".env") or p.endswith("runtime_env.json") for p in changed_files):
                try:
                    targets = [m for m in list(getattr(self.bot, "extensions", {}).keys()) if m.startswith(PREFIX)]
                except Exception: targets = []
            else:
                for sec in sec_changed:
                    mods = self._catmap.get(sec, [])
                    for m in mods:
                        if m and m not in targets: targets.append(m)
        # exclude + dedupe
        targets = [m for m in targets if m and m not in EXCLUDE]
        seen=set(); ordered=[]
        for m in targets:
            if m not in seen: ordered.append(m); seen.add(m)
        targets = ordered
        if not targets:
            logging.info("[hotenv] nothing to reload for changes=%s", changed_files); return
        for mod in targets:
            try: self.bot.unload_extension(mod)
            except Exception: pass
            try:
                self.bot.reload_extension(mod); logging.warning("[hotenv] reloaded: %s", mod); continue
            except Exception:
                try: self.bot.load_extension(mod); logging.warning("[hotenv] loaded : %s", mod)
                except Exception as e: logging.warning("[hotenv] reload failed: %s -> %r", mod, e)
        if BROADCAST:
            try: self.bot.dispatch("hotenv_reload"); logging.info("[hotenv] broadcasted 'hotenv_reload'")
            except Exception: pass
async def setup(bot: Any):
    if _IMPORT_ERR is not None: raise _IMPORT_ERR
    await bot.add_cog(HotEnvAutoReloadOverlay(bot))
def setup(bot: Any):
    if _IMPORT_ERR is not None: raise _IMPORT_ERR
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(bot.add_cog(HotEnvAutoReloadOverlay(bot))); return
    except Exception: pass
    bot.add_cog(HotEnvAutoReloadOverlay(bot))
