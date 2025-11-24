from __future__ import annotations

import logging, json, time
from pathlib import Path
from typing import Any, Dict, Optional

import discord
from satpambot.config.local_cfg import cfg, cfg_int

log = logging.getLogger(__name__)

STATE_FILE = Path("data/status_coalesce/state.json")
WINDOW = int(cfg_int("STATUS_EDIT_WINDOW_SEC", 600) or 600)  # default 10 minutes
raw_titles = cfg("STATUS_COALESCE_TITLES", "") or "Periodic Status"
TITLES = {t.strip() for t in raw_titles.split(",") if t.strip()}

def _load_state() -> Dict[str, Any]:
    try: return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception: return {}
def _save_state(st: Dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")

def _pick_embed(kwargs) -> Optional[discord.Embed]:
    emb = kwargs.get("embed")
    if isinstance(emb, discord.Embed):
        return emb
    embeds = kwargs.get("embeds")
    if isinstance(embeds, (list, tuple)) and embeds and isinstance(embeds[0], discord.Embed):
        return embeds[0]
    return None

async def _edit_or_send(original_send, self, *args, **kwargs):
    emb = _pick_embed(kwargs)
    if not emb or not getattr(emb, "title", None) or str(emb.title) not in TITLES:
        return await original_send(self, *args, **kwargs)

    content = kwargs.get("content", None)
    key = f"{getattr(self, 'id', 0)}::{emb.title}"
    st = _load_state()
    slot = st.get(key, {})
    last_id = int(slot.get("id", 0) or 0)
    ts = int(slot.get("ts", 0) or 0)
    now = int(time.time())

    # Try edit if within window
    if last_id and (now - ts) < WINDOW:
        try:
            msg = await self.fetch_message(last_id)  # works for TextChannel/Thread
            await msg.edit(content=content, embed=emb)
            slot = {"id": last_id, "ts": now}
            st[key] = slot
            _save_state(st)
            return msg
        except Exception:
            pass

    # send new
    msg = await original_send(self, *args, **kwargs)
    try:
        slot = {"id": msg.id, "ts": now}
        st[key] = slot
        _save_state(st)
    except Exception:
        pass
    return msg

def _install():
    try:
        original = discord.abc.Messageable.send
        async def send_wrap(self, *args, **kwargs):
            return await _edit_or_send(original, self, *args, **kwargs)
        discord.abc.Messageable.send = send_wrap  # type: ignore
        log.info("[status_coalescer] installed (titles=%s, window=%ss)", ", ".join(sorted(TITLES)) or "-", WINDOW)
    except Exception as e:
        log.warning("[status_coalescer] install failed: %s", e)

_install()
async def setup(_bot):  # overlay module, no-op
    return