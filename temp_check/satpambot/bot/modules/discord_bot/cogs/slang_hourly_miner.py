from discord.ext import commands
import asyncio
import logging
import random
import time
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

import discord
from discord.ext import commands, tasks

try:
    # prefer project helper if available
    from ..helpers.memory_upsert import upsert_pinned_memory

except Exception:  # pragma: no cover
    upsert_pinned_memory = None  # fallback handled below

LOG = logging.getLogger(__name__)

# --- Module config (do NOT move to ENV) ---
START_DELAY_SEC = 300           # initial delay after on_ready
PERIOD_SEC = 3600               # run every hour
PER_CHANNEL_MESSAGES = 200      # how many recent messages per channel to scan
MAX_UNIQUE_TERMS = 300          # keep top-N unique terms to avoid 4k body
MIN_TERM_LEN = 3                # ignore ultra short tokens
STOPWORDS = {
    "the","and","you","http","https","discord","com","net","org","ini","itu","aja","yg","yang","dan",
    "atau","bgt","banget","gak","ga","kok","nih","dong","dgn","gua","gue","lu","loe","loe","dia",
    "aku","kamu","kalian","kami","kita","gue","aja","si","deh","yah","loh","loh","ya","iya","engga"
}

def _tokenize(text: str) -> List[str]:
    toks = []
    cur = []
    for ch in text.lower():
        if ch.isalnum():
            cur.append(ch)
        else:
            if cur:
                toks.append(''.join(cur))
                cur = []
    if cur:
        toks.append(''.join(cur))
    return toks

def _should_skip_channel(ch: discord.abc.GuildChannel) -> bool:
    # NEVER touch special/system/pinned channels; miner only reads history
    name = getattr(ch, "name", "") or ""
    # keep conservative: skip obvious log channels to reduce noise
    bads = {"ml-state","memory", "log", "logs", "errorlog", "log-botphising", "log-botphishing"}
    for b in bads:
        if b in name.lower():
            return True
    return False

class SlangHourlyMiner(commands.Cog):
    """Collects frequent slang/lingo from recent messages and stores compact summary via pinned memory."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._loop_started = False

    def cog_load(self) -> None:
        # sync method; safe for smoke tools that call it directly
        pass  # actual start happens on_ready to avoid running in smoke/import contexts

    def cog_unload(self) -> None:
        try:
            if self.loop_collect.is_running():
                self.loop_collect.cancel()
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self._loop_started:
            # random jitter 60-180s to reduce collision with other hourly jobs
            jitter = random.uniform(60, 180)
            delay = START_DELAY_SEC + jitter
            LOG.info("[slang_hourly] will start in %.1fs then every %ds", delay, PERIOD_SEC)
            await asyncio.sleep(delay)
            try:
                self.loop_collect.change_interval(seconds=PERIOD_SEC)
                self.loop_collect.start()
                self._loop_started = True
                LOG.info("[slang_hourly] started (delay=%ds, every=%ds, per_channel=%d)",
                         int(delay), PERIOD_SEC, PER_CHANNEL_MESSAGES)
            except RuntimeError:
                # loop could already be running under hot-reload; ignore
                self._loop_started = True

    @tasks.loop(seconds=PERIOD_SEC)
    async def loop_collect(self) -> None:
        try:
            lingo = await self._collect_lingo_snapshot()
            payload = {"lingo": lingo, "ts": int(time.time())}
            ok = False
            if upsert_pinned_memory is not None:
                ok = await upsert_pinned_memory(self.bot, payload)
            else:
                # Fallback: just log to console if helper missing
                LOG.warning("[slang_hourly] memory_upsert helper missing; snapshot size=%d terms", len(lingo.get("top", [])))
                ok = True
            LOG.info("[slang_hourly] memory updated: %s", bool(ok))
        except Exception as e:
            LOG.exception("[slang_hourly] error in loop_collect: %r", e)

    async def _collect_lingo_snapshot(self) -> Dict[str, object]:
        """Scan recent messages across text channels; return compact summary."""
        freq: Counter = Counter()
        per_channel_scanned: Dict[int, int] = defaultdict(int)

        for guild in list(self.bot.guilds or []):
            for ch in guild.text_channels:
                if _should_skip_channel(ch):
                    continue
                try:
                    async for msg in ch.history(limit=PER_CHANNEL_MESSAGES, oldest_first=False):
                        if not msg.content:
                            continue
                        if getattr(msg.author, "bot", False):
                            continue
                        toks = _tokenize(msg.content)
                        for t in toks:
                            if len(t) < MIN_TERM_LEN or t in STOPWORDS:
                                continue
                            freq[t] += 1
                        per_channel_scanned[ch.id] += 1
                except discord.Forbidden:
                    continue
                except discord.HTTPException:
                    continue

        top_terms: List[Tuple[str,int]] = freq.most_common(MAX_UNIQUE_TERMS)
        return {
            "top": top_terms,
            "channels": sum(per_channel_scanned.values()),
            "unique_terms": len(freq),
        }
async def setup(bot: commands.Bot):
    # async setup to be compatible with smoke tools awaiting it
    await bot.add_cog(SlangHourlyMiner(bot))