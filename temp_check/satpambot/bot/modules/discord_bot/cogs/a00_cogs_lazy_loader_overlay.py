
from __future__ import annotations
import os, json, asyncio, logging
from typing import Any, List, Set

try:
    from discord.ext import commands
except Exception as _e:
    commands = None  # type: ignore
    _IMPORT_ERR = _e
else:
    _IMPORT_ERR = None

log = logging.getLogger(__name__)

ENABLE   = os.getenv("COGS_LAZY_ENABLE", "1") == "1"
PREFIX   = os.getenv("COGS_PREFIX", "satpambot.bot.modules.discord_bot.cogs.")
SRC      = (os.getenv("COGS_ALLOWLIST_SRC", "map") or "map").lower()  # env|map|file
ALLOW_CSV= os.getenv("COGS_ALLOWLIST", "")
ALLOW_FILE = os.getenv("COGS_ALLOWLIST_FILE", "data/config/hotenv_reload_exts.list")
ALWAYS_CSV= os.getenv("COGS_ALWAYS", "")
BLOCK_CSV = os.getenv("COGS_BLOCKLIST", "")
AUTOUNLOAD = os.getenv("COGS_AUTOUNLOAD", "1") == "1"
TRIM_ON_READY = os.getenv("COGS_TRIM_ON_READY", "1") == "1"
TRIM_INTERVAL = int(os.getenv("COGS_TRIM_INTERVAL_SEC", "0"))

def _csv(s: str) -> List[str]:
    return [x.strip() for x in (s or "").split(",") if x.strip()]

def _read_file_allowlist(path: str) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
    except Exception:
        return []

def _read_map_allowlist() -> List[str]:
    raw = os.getenv("HOTENV_CATEGORY_MAP_JSON", "").strip()
    if not raw:
        # also try on-disk fallback for convenience
        try:
            with open("data/config/hotenv_category_map.json", "r", encoding="utf-8") as f:
                raw = f.read()
        except Exception:
            raw = ""
    try:
        m = json.loads(raw) if raw else {}
        out = []
        for _, mods in (m or {}).items():
            for mod in mods:
                if mod and mod not in out:
                    out.append(mod)
        return out
    except Exception:
        return []

class LazyCogsLoaderOverlay(commands.Cog):  # type: ignore[misc]
    def __init__(self, bot: Any):
        self.bot = bot
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def cog_load(self):
        if not ENABLE:
            log.info("[cogs-lazy] disabled"); return
        await self._trim_and_load()
        if TRIM_INTERVAL > 0 and (not self._task or self._task.done()):
            self._task = self.bot.loop.create_task(self._looper(), name="cogs_lazy_trim")

    async def cog_unload(self):
        if self._task and not self._task.done():
            self._stop.set(); self._task.cancel()
            try: await self._task
            except asyncio.CancelledError: pass

    async def _looper(self):
        while not self._stop.is_set():
            try:
                await asyncio.sleep(TRIM_INTERVAL)
                await self._trim_and_load()
            except asyncio.CancelledError:
                break
            except Exception:
                log.exception("[cogs-lazy] loop error")

    def _allowlist(self) -> Set[str]:
        allow: List[str] = []
        if SRC == "env":
            allow = _csv(ALLOW_CSV)
        elif SRC == "file":
            allow = _read_file_allowlist(ALLOW_FILE)
        else:
            allow = _read_map_allowlist()
        allow += _csv(ALWAYS_CSV)
        block = set(_csv(BLOCK_CSV))
        # dedupe + exclude blocks + restrict to prefix
        out = []
        seen = set()
        for m in allow:
            if not m or not m.startswith(PREFIX): 
                continue
            if m in seen or m in block:
                continue
            seen.add(m); out.append(m)
        return set(out)

    async def _trim_and_load(self):
        target = self._allowlist()
        if not target:
            log.warning("[cogs-lazy] no allowlist resolved (SRC=%s); skip", SRC)
            return
        loaded = set(getattr(self.bot, "extensions", {}).keys())
        # unload extras
        if AUTOUNLOAD:
            for mod in sorted(list(loaded)):
                if mod.startswith(PREFIX) and mod not in target:
                    try:
                        self.bot.unload_extension(mod)
                        log.info("[cogs-lazy] unloaded: %s", mod)
                    except Exception:
                        pass
        # load missing
        for mod in sorted(list(target)):
            if mod in loaded:
                continue
            try:
                self.bot.load_extension(mod)
                log.info("[cogs-lazy] loaded: %s", mod)
            except Exception as e:
                log.warning("[cogs-lazy] load failed: %s -> %r", mod, e)

    @commands.command(name="cogs_trim")  # type: ignore[attr-defined]
    @commands.is_owner()                 # type: ignore[attr-defined]
    async def cogs_trim_cmd(self, ctx: Any, sub: str="now"):
        if sub == "now":
            await self._trim_and_load()
            await ctx.reply("[cogs-lazy] trim done")
            return
        await ctx.reply("usage: !cogs_trim now")

async def setup(bot: Any):
    if _IMPORT_ERR is not None:
        raise _IMPORT_ERR
    await bot.add_cog(LazyCogsLoaderOverlay(bot))

def setup(bot: Any):
    if _IMPORT_ERR is not None:
        raise _IMPORT_ERR
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(bot.add_cog(LazyCogsLoaderOverlay(bot)))
            return
    except Exception:
        pass
    bot.add_cog(LazyCogsLoaderOverlay(bot))
