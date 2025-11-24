from __future__ import annotations

import asyncio, json, logging, pathlib
from typing import Union, Dict
import discord

log = logging.getLogger(__name__)

_STATE_DIRS = ["/data/satpambot_state", "/tmp"]
_STATE_FILE = "keepers.json"

def _state_path() -> pathlib.Path:
    for d in _STATE_DIRS:
        try:
            p = pathlib.Path(d); p.mkdir(parents=True, exist_ok=True); return p / _STATE_FILE
        except Exception: continue
    return pathlib.Path("/tmp") / _STATE_FILE

class MessageKeeper:
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self._path = _state_path()
        self._lock = asyncio.Lock()
        self._state: Dict[str, Dict[str, int]] = {}
        self._loaded = False

    async def _load(self):
        if self._loaded: return
        try: self._state = json.loads(self._path.read_text("utf-8"))
        except Exception: self._state = {}
        self._loaded = True

    async def _save(self):
        try: self._path.write_text(json.dumps(self._state, ensure_ascii=False, indent=2))
        except Exception: pass

    async def _resolve_channel(self, ref: Union[int, str, discord.abc.Messageable]):
        if isinstance(ref, (discord.TextChannel, discord.Thread, discord.DMChannel)): return ref
        if isinstance(ref, int) or (isinstance(ref, str) and ref.isdigit()):
            cid = int(ref); ch = self.bot.get_channel(cid) or await self.bot.fetch_channel(cid)
            return ch
        if isinstance(ref, str):
            name = ref.lstrip("#")
            for g in getattr(self.bot, "guilds", []):
                ch = discord.utils.get(g.text_channels, name=name)
                if ch: return ch
        return None

    async def _get(self, channel, mid: int):
        try: return await channel.fetch_message(mid)
        except Exception: return None

    async def _create(self, channel, content=None, embed=None, view=None):
        for tries in range(1, 6):
            try: return await channel.send(content=content, embed=embed, view=view)
            except discord.HTTPException as e:
                status = getattr(e, "status", None)
                text = ""
                try: text = await e.response.text() if e.response else ""
                except Exception: pass
                if status == 429 or ("cloudflare" in text.lower() and "1015" in text):
                    base = 5 if "1015" in text else 1.5
                    await asyncio.sleep(min(60, base * tries)); continue
                raise
        return None

    async def _edit(self, msg: discord.Message, **kwargs):
        for tries in range(1, 6):
            try: return await msg.edit(**kwargs)
            except discord.HTTPException as e:
                status = getattr(e, "status", None)
                text = ""
                try: text = await e.response.text() if e.response else ""
                except Exception: pass
                if status == 429 or ("cloudflare" in text.lower() and "1015" in text):
                    base = 5 if "1015" in text else 1.5
                    await asyncio.sleep(min(60, base * tries)); continue
                raise

    async def update(self, channel_ref: Union[int, str, discord.abc.Messageable], key: str, *, content: str = None, embed=None, view=None):
        assert content is not None or embed is not None, "content or embed required"
        await self._load()
        channel = await self._resolve_channel(channel_ref)
        if not channel:
            log.warning("[keeper] channel %r not found", channel_ref); return None

        async with self._lock:
            cs = self._state.get(str(getattr(channel, "id", 0)) or "0") or {}
            mid = cs.get(key)
            msg = await self._get(channel, mid) if mid else None
            header = f"[{key}] " if content and not content.startswith("[") else ""
            if not msg:
                new_msg = await self._create(channel, content=header + (content or ""), embed=embed, view=view)
                if not new_msg: return None
                cs[key] = new_msg.id
                self._state[str(getattr(channel, "id", 0)) or "0"] = cs
                await self._save()
                return new_msg
            return await msg.edit(content=header + (content or "") if content is not None else discord.utils.MISSING,
                                  embed=embed if embed is not None else discord.utils.MISSING,
                                  view=view if view is not None else discord.utils.MISSING)

def get_keeper(bot: discord.Client) -> MessageKeeper:
    inst = getattr(bot, "_satpam_msg_keeper", None)
    if not isinstance(inst, MessageKeeper):
        inst = MessageKeeper(bot); setattr(bot, "_satpam_msg_keeper", inst)
    return inst
