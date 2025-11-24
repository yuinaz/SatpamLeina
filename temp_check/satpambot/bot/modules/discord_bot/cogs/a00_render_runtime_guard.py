
from discord.ext import commands
import asyncio
import json
import logging
import os
import platform
import sys
from pathlib import Path
from typing import Any, Dict

LOG = logging.getLogger(__name__)

# --------- Tunables (safe defaults for Render free) ---------
DEFAULT_QNA_CHANNEL_ID = int(os.getenv("QNA_CHANNEL_ID", "1426571542627614772"))
CREATE_DEFAULT_JSON = True
JSON_DIRS = [
    Path("satpambot/bot/data"),
    Path("data/neuro-lite"),
]
JSON_EXPECTED = {
    Path("satpambot/bot/data/xp_store.json"): {
        "version": 2, "users": {}, "awards": [], "stats": {}, "updated_at": 0
    },
    Path("satpambot/bot/data/xp_awarded_ids.json"): {
        "ids": [], "updated_at": 0
    },
    Path("data/neuro-lite/observe_metrics.json"): {},
    Path("data/neuro-lite/learn_progress_junior.json"): {},
}
# ------------------------------------------------------------

def _ensure_parent(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)

def _is_json_valid(p: Path) -> bool:
    try:
        if not p.exists() or p.stat().st_size == 0:
            return False
        with p.open("r", encoding="utf-8") as f:
            json.load(f)
        return True
    except Exception:
        return False

def _write_json(p: Path, obj: Any):
    _ensure_parent(p)
    with p.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def _coerce_qna_ids() -> int:
    # try to coerce multiple modules to the same QNA id
    qid = DEFAULT_QNA_CHANNEL_ID
    mods = [
        "satpambot.bot.modules.discord_bot.cogs.a24_qna_channel_overlay",
        "satpambot.bot.modules.discord_bot.cogs.selfheal_learning_bridge",
        "satpambot.bot.modules.discord_bot.cogs.neuro_shadow_bridge",
        "satpambot.bot.modules.discord_bot.cogs.learning_passive_observer",
    ]
    for m in mods:
        try:
            mod = __import__(m, fromlist=["*"])
            if hasattr(mod, "QNA_CHANNEL_ID"):
                setattr(mod, "QNA_CHANNEL_ID", qid)
                LOG.info("[render-guard] forced %s.QNA_CHANNEL_ID=%s", m, qid)
        except Exception:
            continue
    return qid

def _install_embed_scribe_shim():
    try:
        from satpambot.bot.utils import embed_scribe as es
        if not hasattr(es.EmbedScribe, "upsert"):
            def upsert(self, *args, **kwargs):
                if hasattr(self, "update"):
                    return self.update(*args, **kwargs)
                if hasattr(self, "send"):
                    return self.send(*args, **kwargs)
                LOG.debug("EmbedScribe shim: no update/send"); return None
            setattr(es.EmbedScribe, "upsert", upsert)
            LOG.info("[render-guard] EmbedScribe.upsert shim installed")
    except Exception as e:
        LOG.warning("[render-guard] EmbedScribe shim skipped: %r", e)

def _env_summary() -> Dict[str, Any]:
    keys = [
        "RENDER", "RENDER_SERVICE_ID", "RENDER_SERVICE_NAME",
        "GROQ_API_KEY", "GOOGLE_API_KEY", "UPSTASH_REDIS_REST_URL",
        "UPSTASH_REDIS_REST_TOKEN", "QNA_CHANNEL_ID"
    ]
    redacted = {}
    for k in keys:
        v = os.getenv(k)
        if v is None:
            redacted[k] = None
        else:
            redacted[k] = f"set({len(v)} chars)" if len(v) > 6 else "set"
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "env": redacted,
        "cwd": str(Path.cwd())
    }

class RenderRuntimeGuard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._done = False
        try:
            # schedule after bot ready
            bot.loop.create_task(self._preflight())
        except Exception:
            asyncio.create_task(self._preflight())

    async def _preflight(self):
        # wait until discord client is ready (if available)
        try:
            await self.bot.wait_until_ready()
        except Exception:
            pass

        if self._done:
            return
        self._done = True

        LOG.info("[render-guard] boot summary: %s", _env_summary())
        _install_embed_scribe_shim()
        qid = _coerce_qna_ids()
        LOG.info("[render-guard] QNA channel pinned to %s", qid)

        if CREATE_DEFAULT_JSON:
            for d in JSON_DIRS:
                d.mkdir(parents=True, exist_ok=True)
            for p, fallback in JSON_EXPECTED.items():
                if not _is_json_valid(p):
                    _write_json(p, fallback)
                    LOG.warning("[render-guard] wrote default JSON: %s", p)

        LOG.info("[render-guard] preflight complete")
async def setup(bot):
    await bot.add_cog(RenderRuntimeGuard(bot))