
from discord.ext import commands
import os, asyncio, logging, json, hashlib, time
from pathlib import Path
from collections import OrderedDict

try:
    from ....helpers import hotenv_segment_utils as H
except Exception:
    H = None

log = logging.getLogger(__name__)

DEFAULT_PATHS = [
    "overrides.render-free.json",
    "overrides.render_free.json",
    "overrides.json",
]

def _find_path() -> Path:
    raw = os.getenv("HOTENV_OVERRIDES_PATH","").strip()
    if raw:
        p = Path(raw)
        if p.exists():
            return p
    for name in DEFAULT_PATHS:
        p = Path(name)
        if p.exists():
            return p
    return Path("overrides.render-free.json")  # fallback

class HotenvDebounceGuard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.debounce_ms = int(os.getenv("HOTENV_DEBOUNCE_MS","1200"))
        self.path = _find_path()
        self.cache_file = Path(os.getenv("HOTENV_CACHE_FILE","data/cache/hotenv_segment_hash.json"))
        self._pending = 0
        self._timer_task = None
        self._last_mtime = 0.0
        self._last_seg_hash = {}
        self._lock = asyncio.Lock()
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_cache()
        log.info("[hotenv-guard] watching %s | debounce=%sms", self.path, self.debounce_ms)

    # ---------- cache ----------
    def _load_cache(self):
        try:
            if self.cache_file.exists():
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._last_seg_hash = data.get("segments", {})
                self._last_mtime = float(data.get("mtime", 0.0))
        except Exception:
            self._last_seg_hash = {}
            self._last_mtime = 0.0

    def _save_cache(self, seg_hash: dict, mtime: float):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump({"segments": seg_hash, "mtime": mtime}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ---------- helpers ----------
    def _read_env(self) -> "OrderedDict[str,str] | None":
        try:
            if not self.path.exists():
                return None
            text = self.path.read_text(encoding="utf-8")
            data = json.loads(text, object_pairs_hook=OrderedDict)
            env = data.get("env")
            if not isinstance(env, (dict, OrderedDict)):
                return None
            return OrderedDict(env.items())
        except Exception as e:
            log.warning("[hotenv-guard] read error: %r", e)
            return None

    def _current_seg_hash(self, env_od) -> dict:
        if not H:
            # fallback: one-shot hash of whole env
            blob = json.dumps(env_od, ensure_ascii=False, sort_keys=True, separators=(',',':'))
            return {"ROOT": hashlib.sha1(blob.encode()).hexdigest()}
        return H.sha1_segments(env_od)

    # ---------- core ----------
    async def _schedule_fire(self):
        if self._timer_task and not self._timer_task.done():
            return
        # debounce timer
        async def _wait_and_fire():
            await asyncio.sleep(self.debounce_ms / 1000.0)
            await self._handle_fire()
        self._timer_task = asyncio.create_task(_wait_and_fire(), name="hotenv_debounce")

    async def _handle_fire(self):
        async with self._lock:
            pending = self._pending
            self._pending = 0
        if pending <= 0:
            return
        # read file & compare
        env_od = self._read_env()
        if env_od is None:
            log.warning("[hotenv-guard] no env found in %s", self.path)
            return
        try:
            mtime = self.path.stat().st_mtime
        except Exception:
            mtime = time.time()

        seg_hash = self._current_seg_hash(env_od)
        prev = self._last_seg_hash or {}
        if seg_hash == prev:
            log.warning("[hotenv-change] ignored hotenv_reload (no config change)")
            return

        # compute change sets for logs
        if H:
            added, removed, changed = H.diff_segments(prev, seg_hash)
        else:
            added, removed, changed = [], [], ["ROOT"]

        # update cache
        self._last_seg_hash = seg_hash
        self._last_mtime = mtime
        self._save_cache(seg_hash, mtime)

        # forward a single consolidated event with details
        payload = {"segments_added": added, "segments_removed": removed, "segments_changed": changed, "mtime": mtime}
        log.info("[hotenv-change] apply -> added=%s removed=%s changed=%s", added, removed, changed)
        try:
            self.bot.dispatch("hotenv_change", payload)
        except Exception:
            pass

    # ---------- event hooks ----------
    async def on_hotenv_reload(self, *args, **kwargs):
        # coalesce multiple broadcasts
        self._pending += 1
        if self._pending > 1:
            log.warning("[hotenv-debounce] coalesced %s hotenv_reload event(s); waited=%sms", self._pending, self.debounce_ms)
        await self._schedule_fire()

async def setup(bot: commands.Bot):
    await bot.add_cog(HotenvDebounceGuard(bot))
