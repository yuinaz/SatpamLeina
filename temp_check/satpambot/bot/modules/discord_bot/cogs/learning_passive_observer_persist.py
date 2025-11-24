from discord.ext import commands
import os, json, logging
from datetime import datetime, timezone

import discord

log = logging.getLogger(__name__)

def _persist_path() -> str:
    base = os.getenv("NEUROLITE_STATE_DIR")
    if not base:
        base = os.path.join(os.path.dirname(__file__), "..","..","..","..","..","..","data","neuro-lite")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "learning_local.json")

def _read_local() -> dict:
    p = _persist_path()
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _write_local(d: dict):
    try:
        with open(_persist_path(), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

class LearningPassiveObserverPersist(commands.Cog):
    """Leina: local observability for passive events (import-safe)."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_message")
    async def _on_message(self, message: discord.Message):
        if message.author.bot:
            return
        try:
            d = _read_local()
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            item = d.get(today) or {"messages": 0, "last_channel_id": None, "last_ts": None}
            item["messages"] = int(item["messages"]) + 1
            item["last_channel_id"] = int(message.channel.id)
            item["last_ts"] = int(datetime.now(timezone.utc).timestamp())
            d[today] = item
            _write_local(d)
        except Exception as e:
            log.debug("[persist] write failed: %s", e)
async def setup(bot: commands.Bot):
    await bot.add_cog(LearningPassiveObserverPersist(bot))