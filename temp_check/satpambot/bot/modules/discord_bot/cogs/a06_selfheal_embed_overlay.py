from __future__ import annotations

import logging, time, json
from pathlib import Path
import discord
from satpambot.config.local_cfg import cfg_int, cfg
from .a06_status_embed_helper import status_embed

log = logging.getLogger(__name__)
STATE = Path("data/selfheal/embed_state.json")
WINDOW = int(cfg_int("STATUS_EDIT_WINDOW_SEC", 600) or 600)  # 10 menit

def _load_state():
    try: return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception: return {}
def _save_state(st):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")

async def install_embed_bridge(bot):
    try:
        mod = __import__("satpambot.bot.modules.discord_bot.cogs.selfheal_autofix", fromlist=["SelfHealAutoFix"])
    except Exception as e:
        log.warning("[selfheal_embed] selfheal_autofix not loaded yet: %s", e); return
    cls = getattr(mod, "SelfHealAutoFix", None)
    if not cls: return

    async def _ensure_log_thread():
        # reuse underlying helper if exists
        try:
            return await mod._ensure_log_thread(bot)  # type: ignore[attr-defined]
        except Exception:
            ch = bot.get_channel(int(cfg("LOG_CHANNEL_ID", 0) or 0))
            return ch, None

    async def _post_embed(content: str, title: str="Self-Heal", color: int=0x2b9dff, fields: dict|None=None):
        ch, th = await _ensure_log_thread()
        if not ch and not th: return
        st = _load_state()
        now = int(time.time())
        last = st.get("last", {})
        msg_id = int(last.get("id", 0) or 0)
        ts = int(last.get("ts", 0) or 0)
        # Build embed
        emb = status_embed(title, content, color=color, fields=fields)
        # Within window? -> edit existing; else create new
        try:
            target = th or ch
            if msg_id and (now - ts) < WINDOW:
                try:
                    msg = await target.fetch_message(msg_id)
                    await msg.edit(embed=emb)
                    st["last"] = {"id": msg_id, "ts": now}
                    _save_state(st)
                    return
                except Exception:
                    pass
            msg = await target.send(embed=emb)
            st["last"] = {"id": msg.id, "ts": now}
            _save_state(st)
        except Exception as e:
            log.warning("[selfheal_embed] post failed: %s", e)

    # Monkeypatch the _post used by selfheal_autofix
    setattr(mod, "_post", _post_embed)
    log.info("[selfheal_embed] _post bridged to embed coalescer")
async def setup(bot):  # this is a standalone extension
    await install_embed_bridge(bot)