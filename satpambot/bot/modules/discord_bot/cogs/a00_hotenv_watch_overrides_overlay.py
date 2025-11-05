from __future__ import annotations
import os, asyncio, logging, hashlib, json
from pathlib import Path
from typing import Optional
from discord.ext import commands

log = logging.getLogger(__name__)

def _env_bool(k: str, default: bool=False) -> bool:
    v = os.getenv(k)
    if v is None or v == "":
        return default
    return str(v).lower() in ("1","true","yes","on")

def _env_int(k: str, d: int) -> int:
    try:
        return int(os.getenv(k, str(d)) or d)
    except Exception:
        return d

def _find_overrides_file(explicit: Optional[str]=None) -> Optional[Path]:
    if explicit:
        p = Path(explicit)
        if p.exists(): return p
    # Search upwards and cwd for data/config/overrides.render-free.json
    candidates = []
    here = Path(__file__).resolve()
    p = here
    for _ in range(8):
        candidates.append(p / "data" / "config" / "overrides.render-free.json")
        p = p.parent
    candidates.append(Path.cwd() / "data" / "config" / "overrides.render-free.json")
    for c in candidates:
        if c.exists(): return c
    return None

class HotenvWatchOverrides(commands.Cog):
    """Watch overrides.render-free.json and dispatch 'hotenv_reload' when valid JSON changes.
    - Starts watcher ASAP: tries create_task in __init__; if loop not running, will start on_ready.
    - No dependency on bot.loop.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.enable = _env_bool("HOTENV_WATCH_ENABLE", True)
        self.interval_ms = _env_int("HOTENV_WATCH_INTERVAL_MS", 1500)
        self.explicit_path = os.getenv("HOTENV_FILE", "")
        self.overrides_path: Optional[Path] = _find_overrides_file(self.explicit_path)
        self._task: Optional[asyncio.Task] = None
        self._last_hash = ""
        self._start_pending = False
        if self.enable and self.overrides_path:
            try:
                self._task = asyncio.create_task(self._run())
            except Exception:
                # No running loop yet — defer to on_ready
                self._start_pending = True

    async def cog_unload(self):
        t = self._task
        self._task = None
        if t:
            t.cancel()
            try:
                await t
            except Exception:
                pass

    def _fingerprint(self, data: bytes) -> str:
        return hashlib.sha1(data).hexdigest()

    async def _run(self):
        # prime last
        try:
            if self.overrides_path and self.overrides_path.exists():
                self._last_hash = self._fingerprint(self.overrides_path.read_bytes())
        except Exception:
            self._last_hash = ""
        # poll loop
        while True:
            try:
                await asyncio.sleep(max(self.interval_ms, 200) / 1000.0)
                if not self.overrides_path or not self.overrides_path.exists():
                    continue
                b = self.overrides_path.read_bytes()
                fp = self._fingerprint(b)
                if fp != self._last_hash:
                    self._last_hash = fp
                    try:
                        json.loads(b.decode("utf-8"))
                        self.bot.dispatch("hotenv_reload")
                        log.info("[hotenv] broadcasted 'hotenv_reload'")
                    except Exception as e:
                        log.warning("[hotenv] ignored change (invalid JSON): %r", e)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.exception("[hotenv] watch loop error: %r", e)

    @commands.Cog.listener()
    async def on_ready(self):
        if self._start_pending and self.enable and self.overrides_path and not self._task:
            try:
                self._task = asyncio.create_task(self._run())
                self._start_pending = False
            except Exception as e:
                log.warning("[hotenv] failed to start on_ready: %r", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(HotenvWatchOverrides(bot))
