from __future__ import annotations

from discord.ext import commands

import asyncio, json, logging, os, hashlib, re
from typing import Any, Dict, Optional, Tuple

LOG = logging.getLogger(__name__)

def _coerce_bool(v: Any) -> bool:
    if isinstance(v, bool): return v
    if isinstance(v, (int, float)): return bool(int(v))
    if isinstance(v, str): return v.strip().lower() in {"1","true","yes","on","enabled","enable"}
    return False

_JSONC_BLOCK = re.compile(r"/\*.*?\*/", re.S)
_JSONC_LINE  = re.compile(r"(?m)//.*$")
def _strip_json_comments(s: str) -> str:
    return _JSONC_LINE.sub("", _JSONC_BLOCK.sub("", s))

def _parse_json(raw: str) -> Optional[dict]:
    try:
        data = json.loads(_strip_json_comments(raw))
        return data if isinstance(data, dict) else None
    except Exception:
        return None

def _set_env_bool(key: str, val: Optional[Any]) -> None:
    if val is None: return
    os.environ[key] = "1" if _coerce_bool(val) else "0"

def _set_env_str(key: str, val: Optional[Any]) -> None:
    if val is None: return
    os.environ[key] = str(val)

def _apply_to_dm_muzzle(mode: Optional[str]) -> None:
    if not mode: return
    os.environ["DM_MUZZLE"] = str(mode).lower()
    try:
        from . import dm_muzzle as dm  # type: ignore
        for name in ("set_mode","set_dm_muzzle_mode","configure"):
            fn = getattr(dm, name, None)
            if callable(fn):
                fn(str(mode).lower())
                LOG.info("[livecfg] dm_muzzle mode -> %s (via %s)", mode, name)
                break
    except Exception as e:
        LOG.debug("[livecfg] dm_muzzle live apply not available: %s", e)

def _persist_runtime_flags() -> None:
    dst = os.getenv("RUNTIME_FLAGS_PATH", "data/runtime_flags.json")
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        flags = {
            "DM_MUZZLE": os.environ.get("DM_MUZZLE",""),
            "SELFHEAL_ENABLE": os.environ.get("SELFHEAL_ENABLE",""),
            "AUTOMATON_ENABLE": os.environ.get("AUTOMATON_ENABLE",""),
            "SELFHEAL_QUIET": os.environ.get("SELFHEAL_QUIET",""),
            "AUTOMATON_QUIET": os.environ.get("AUTOMATON_QUIET",""),
            "SELFHEAL_THREAD_DISABLE": os.environ.get("SELFHEAL_THREAD_DISABLE",""),
            "AUTOMATON_THREAD_DISABLE": os.environ.get("AUTOMATON_THREAD_DISABLE",""),
            "LOG_CHANNEL_ID": os.environ.get("LOG_CHANNEL_ID",""),
            "SELFHEAL_THREAD_CHANNEL_ID": os.environ.get("SELFHEAL_THREAD_CHANNEL_ID",""),
            "AUTOMATON_THREAD_CHANNEL_ID": os.environ.get("AUTOMATON_THREAD_CHANNEL_ID",""),
        }
        with open(dst,"w",encoding="utf-8") as f:
            json.dump(flags,f,indent=2,ensure_ascii=False)
    except Exception as e:
        LOG.warning("[livecfg] cannot write %s: %s", dst, e)

def _apply_livecfg(bot: commands.Bot, cfg: Dict[str, Any]) -> Dict[str, Any]:
    _set_env_bool("SELFHEAL_ENABLE", cfg.get("selfheal"))
    _set_env_bool("AUTOMATON_ENABLE", cfg.get("automaton"))
    _set_env_bool("SELFHEAL_QUIET", cfg.get("selfheal_quiet"))
    _set_env_bool("AUTOMATON_QUIET", cfg.get("automaton_quiet"))
    _set_env_bool("SELFHEAL_THREAD_DISABLE", cfg.get("selfheal_thread_disable"))
    _set_env_bool("AUTOMATON_THREAD_DISABLE", cfg.get("automaton_thread_disable"))

    _set_env_str("LOG_CHANNEL_ID", cfg.get("log_channel_id"))
    _set_env_str("SELFHEAL_THREAD_CHANNEL_ID", cfg.get("selfheal_thread_channel_id"))
    _set_env_str("AUTOMATON_THREAD_CHANNEL_ID", cfg.get("automaton_thread_channel_id"))

    dm_mode = cfg.get("dm_muzzle_mode") or cfg.get("dm_muzzle")
    if isinstance(dm_mode, (str,int)):
        _apply_to_dm_muzzle(str(dm_mode))

    try:
        bot.dispatch("livecfg_update", dict(cfg))
    except Exception as e:
        LOG.debug("[livecfg] dispatch error: %s", e)

    _persist_runtime_flags()
    return {
        "DM_MUZZLE": os.environ.get("DM_MUZZLE"),
        "SELFHEAL_ENABLE": os.environ.get("SELFHEAL_ENABLE"),
        "AUTOMATON_ENABLE": os.environ.get("AUTOMATON_ENABLE"),
        "SELFHEAL_QUIET": os.environ.get("SELFHEAL_QUIET"),
        "AUTOMATON_QUIET": os.environ.get("AUTOMATON_QUIET"),
        "SELFHEAL_THREAD_DISABLE": os.environ.get("SELFHEAL_THREAD_DISABLE"),
        "AUTOMATON_THREAD_DISABLE": os.environ.get("AUTOMATON_THREAD_DISABLE"),
        "LOG_CHANNEL_ID": os.environ.get("LOG_CHANNEL_ID"),
        "SELFHEAL_THREAD_CHANNEL_ID": os.environ.get("SELFHEAL_THREAD_CHANNEL_ID"),
        "AUTOMATON_THREAD_CHANNEL_ID": os.environ.get("AUTOMATON_THREAD_CHANNEL_ID"),
    }

async def _read_file(path: str):
    try:
        with open(path,"r",encoding="utf-8") as f:
            raw = f.read()
        return _parse_json(raw), raw
    except FileNotFoundError:
        return None, None
    except Exception:
        return None, None

async def _read_url(url: str):
    import urllib.request
    try:
        def _fetch() -> str:
            req = urllib.request.Request(url, headers={"User-Agent":"SatpamLiveCfg/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                charset = r.headers.get_content_charset() or "utf-8"
                return r.read().decode(charset, "replace")
        raw = await asyncio.to_thread(_fetch)
        return _parse_json(raw), raw
    except Exception:
        return None, None

JSON_BLOCK = re.compile(r"```(?:json)?\s*(.*?)```", re.S|re.I)
def _extract_json_from_text(text: str):
    m = JSON_BLOCK.search(text or "")
    if m: return m.group(1).strip()
    return text.strip() if (text and text.strip().startswith("{")) else None

async def _read_discord_message(bot: commands.Bot, channel_id: int, message_id: int):
    try:
        chan = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
        msg  = await chan.fetch_message(message_id)
        raw  = _extract_json_from_text(msg.content or "")
        if not raw: return None, None
        return _parse_json(raw), raw
    except Exception:
        return None, None

async def _read_discord_topic(bot: commands.Bot, channel_id: int):
    try:
        chan = await bot.fetch_channel(channel_id)
        raw  = chan.topic or ""
        rawj = _extract_json_from_text(raw)
        if not rawj: return None, None
        return _parse_json(rawj), rawj
    except Exception:
        return None, None

class LiveConfigWatcher(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.source = os.getenv("LIVE_CONFIG_SOURCE","file").lower().strip()
        self.path   = os.getenv("LIVE_CONFIG_PATH","satpambot_config.live.json")
        self.url    = os.getenv("LIVE_CONFIG_URL","")
        self.chan_id = int(os.getenv("LIVE_CONFIG_DISCORD_CHANNEL_ID","0") or 0)
        self.msg_id  = int(os.getenv("LIVE_CONFIG_DISCORD_MESSAGE_ID","0") or 0)
        default_poll = 10.0 if self.source == "url" else 4.0
        try: self.poll = float(os.getenv("LIVE_CONFIG_POLL_INTERVAL", str(default_poll)))
        except Exception: self.poll = default_poll
        self._task = asyncio.create_task(self._loop())
        self._last_hash = None
        LOG.info("[livecfg] source=%s poll=%.1fs", self.source, self.poll)

    async def _fetch_once(self):
        if self.source == "file":
            return await _read_file(self.path)
        if self.source == "url":
            return await _read_url(self.url)
        if self.source == "discord_message":
            if not (self.chan_id and self.msg_id): return (None, None)
            return await _read_discord_message(self.bot, self.chan_id, self.msg_id)
        if self.source == "discord_topic":
            if not self.chan_id: return (None, None)
            return await _read_discord_topic(self.bot, self.chan_id)
        return (None, None)

    async def _loop(self):
        await self.bot.wait_until_ready()
        while True:
            try:
                cfg, raw = await self._fetch_once()
                if cfg is not None and raw is not None:
                    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
                    if h != self._last_hash:
                        summary = _apply_livecfg(self.bot, cfg)
                        self._last_hash = h
                        LOG.info("[livecfg] applied: %s", summary)
            except asyncio.CancelledError:
                break
            except Exception:
                pass
            await asyncio.sleep(self.poll)

    def cog_unload(self):
        if self._task: self._task.cancel()

    @commands.command(name="livecfg")
    @commands.has_permissions(administrator=True)
    async def livecfg_status(self, ctx: commands.Context, subcmd: Optional[str]=None, *, tail: str=""):
        if subcmd in {"reload","apply"}:
            cfg, raw = await self._fetch_once()
            if cfg is None:
                await ctx.reply("livecfg: source unreadable."); return
            summary = _apply_livecfg(self.bot, cfg)
            await ctx.reply(f"livecfg re-applied ({self.source}): {summary}"); return
        if subcmd == "source":
            parts = (tail or "").strip().split(None,1)
            if not parts:
                await ctx.reply(f"current source={self.source}, poll={self.poll}s"); return
            mode = parts[0].lower(); arg = (parts[1] if len(parts)>1 else "").strip()
            if mode in {"file","url","discord_message","discord_topic"}:
                self.source = mode
                if mode == "file" and arg: self.path = arg
                if mode == "url"  and arg: self.url  = arg
                await ctx.reply(f"livecfg source set -> {self.source}"); return
            await ctx.reply("usage: !livecfg source <file|url|discord_message|discord_topic> [arg]"); return
        await ctx.reply(f"livecfg: source={self.source} poll={self.poll}s hash={self._last_hash}")
async def setup(bot: commands.Bot):
    await bot.add_cog(LiveConfigWatcher(bot))