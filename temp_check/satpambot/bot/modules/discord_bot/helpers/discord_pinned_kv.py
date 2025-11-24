import os, json, asyncio, logging, inspect
from typing import Optional, Dict, Any

log = logging.getLogger(__name__)

# === Built-in defaults (checked-in to repo, edit here if needed) ============
_DEFAULTS = {
    "KV_JSON_CHANNEL_ID": "1400375184048787566",
    "KV_JSON_MESSAGE_ID": "1432060859252998268",
    "KV_JSON_MARKER": "leina:xp_status",
    "KV_JSON_MIN_EDIT_SEC": "2",
    "XP_SENIOR_KEY": "xp:bot:senior_total",
}
# ============================================================================

def _getenv(name: str, default_key: Optional[str] = None) -> Optional[str]:
    """Try os.environ first (loader merges JSON→ENV), else built-in _DEFAULTS."""
    v = os.getenv(name, None)
    if (v is None or v == "") and default_key:
        v = _DEFAULTS.get(default_key)
    return v

def _env_int(name: str, default_key: Optional[str]) -> Optional[int]:
    v = _getenv(name, default_key)
    if v is None or v == "":
        return None
    try:
        return int(v)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return None

def _env_str(name: str, default_key: Optional[str]) -> Optional[str]:
    v = _getenv(name, default_key)
    return v

KV_CHAN = _env_int("KV_JSON_CHANNEL_ID", "KV_JSON_CHANNEL_ID")
KV_MSG  = _env_int("KV_JSON_MESSAGE_ID", "KV_JSON_MESSAGE_ID")
KV_MARK = _env_str("KV_JSON_MARKER", "KV_JSON_MARKER") or "leina:xp_status"
KV_CODELANG = "json"

try:
    _min_edit = float(_getenv("KV_JSON_MIN_EDIT_SEC","KV_JSON_MIN_EDIT_SEC") or "2")
except Exception:
    _min_edit = 2.0

_CONTENT_TMPL = """{marker}
```json
{payload}
```"""

class PinnedJSONKV:
    """
    Minimal JSON KV store backed by a pinned Discord message.
    Stores a single JSON object mapping string keys -> scalar/objects.
    """
    def __init__(self, bot):
        self.bot = bot
        self._msg_id = None
        self._lock = asyncio.Lock()
        self._last_edit_ts = 0.0
        self._min_edit_interval = _min_edit
        self._cache: Dict[str, Any] = {}

    # ---- public ------------------------------------------------------------
    async def ensure_ready(self) -> Optional[int]:
        try:
            mid = await self._resolve_message_id()
            return mid
        except Exception as e:
            log.warning("[kv-json] ensure_ready failed: %r", e)
            return None

    async def get_map(self) -> Dict[str, Any]:
        async with self._lock:
            await self._ensure_message()
            msg = await self._fetch_message()
            data = self._parse_map(msg)
            if isinstance(data, dict):
                self._cache = data
                return dict(data)
            return {}

    async def get(self, key: str, default=None):
        m = await self.get_map()
        return m.get(key, default)

    async def set_multi(self, updates: Dict[str, Any]) -> bool:
        async with self._lock:
            await self._ensure_message()
            msg = await self._fetch_message()
            data = self._parse_map(msg) or {}
            changed = False
            for k, v in updates.items():
                if data.get(k) != v:
                    data[k] = v
                    changed = True
            if not changed:
                return False
            now = asyncio.get_running_loop().time()
            if now - self._last_edit_ts < self._min_edit_interval:
                await asyncio.sleep(self._min_edit_interval - (now - self._last_edit_ts))
            payload = json.dumps(data, ensure_ascii=False, separators=(",",":"))
            content = _CONTENT_TMPL.format(marker=KV_MARK or "", payload=payload)
            await msg.edit(content=content)
            try:
                await msg.pin()
            except Exception:
                pass
            self._cache = data
            self._last_edit_ts = asyncio.get_running_loop().time()
            return True

    async def incr(self, key: str, delta: int) -> int:
        async with self._lock:
            await self._ensure_message()
            msg = await self._fetch_message()
            data = self._parse_map(msg) or {}
            cur = 0
            try:
                cur = int(data.get(key, 0))
            except Exception:
                try:
                    cur = int(float(data.get(key, 0)))
                except Exception:
                    cur = 0
            newv = cur + int(delta)
            data[key] = newv
            payload = json.dumps(data, ensure_ascii=False, separators=(",",":"))
            content = _CONTENT_TMPL.format(marker=KV_MARK or "", payload=payload)
            await msg.edit(content=content)
            try:
                await msg.pin()
            except Exception:
                pass
            self._cache = data
            self._last_edit_ts = asyncio.get_running_loop().time()
            return newv

    # ---- internals ---------------------------------------------------------
    def _parse_map(self, msg) -> Optional[Dict[str, Any]]:
        try:
            content = msg.content or ""
            start = content.find("```json")
            if start == -1:
                start = content.find("```")
            if start == -1:
                return {}
            end = content.find("```", start+3)
            if end == -1:
                return {}
            blob = content[start:].split("```",1)[1]
            if "\n" in blob:
                blob = blob.split("\n",1)[1]
            blob = blob.strip()
            if blob.endswith("```"):
                blob = blob[:-3].strip()
            return json.loads(blob) if blob else {}
        except Exception:
            return {}

    async def _resolve_message_id(self) -> Optional[int]:
        if self._msg_id:
            return self._msg_id
        chan_id = KV_CHAN
        if not chan_id:
            return None
        ch = self.bot.get_channel(chan_id)
        if ch is None:
            try:
                ch = await self.bot.fetch_channel(chan_id)
            except Exception:
                return None
        msg_id = KV_MSG
        if msg_id:
            try:
                msg = await ch.fetch_message(msg_id)
                self._msg_id = int(msg.id)
                return self._msg_id
            except Exception:
                pass
        try:
            pins = await ch.pins()
            for m in pins:
                if m.content and (KV_MARK or "") in m.content:
                    self._msg_id = int(m.id)
                    return self._msg_id
        except Exception:
            pass
        try:
            content = _CONTENT_TMPL.format(marker=KV_MARK or "", payload="{}")
            m = await ch.send(content)
            try:
                await m.pin()
            except Exception:
                pass
            self._msg_id = int(m.id)
            return self._msg_id
        except Exception as e:
            log.warning("[kv-json] create message failed: %r", e)
            return None

    async def _ensure_message(self):
        if not self._msg_id:
            await self._resolve_message_id()

    async def _fetch_message(self):
        chan_id = KV_CHAN
        ch = self.bot.get_channel(chan_id)
        if ch is None:
            ch = await self.bot.fetch_channel(chan_id)
        msg = await ch.fetch_message(self._msg_id)
        return msg
