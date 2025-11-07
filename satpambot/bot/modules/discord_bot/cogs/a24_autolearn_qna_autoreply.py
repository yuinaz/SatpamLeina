from __future__ import annotations
import os, json, random, logging, asyncio
from pathlib import Path
import discord
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

# ---------------- Env helpers ----------------
def _ebool(k: str, d: bool=False) -> bool:
    v = os.getenv(k)
    if v is None or v == "":
        return d
    return str(v).lower() in ("1","true","yes","on")

def _eint(k: str, d: int) -> int:
    try:
        return int(os.getenv(k, str(d)) or d)
    except Exception:
        return d

def _channel_id() -> int:
    try:
        return int(os.getenv("QNA_CHANNEL_ID") or os.getenv("LEARNING_QNA_CHANNEL_ID") or "0")
    except Exception:
        return 0

def _topics_path() -> Path:
    # Accept both QNA_TOPICS_FILE and QNA_TOPICS_PATH; default to repo data file
    p = os.getenv("QNA_TOPICS_FILE") or os.getenv("QNA_TOPICS_PATH") or "data/config/qna_topics.json"
    path = Path(p)
    if not path.exists():
        # try satpambot/ prefix if running from repo root
        alt = Path("satpambot")/p
        if alt.exists():
            path = alt
    return path

def _enabled() -> bool:
    # runtime check each tick
    return _ebool("QNA_AUTOREPLY_SEED_ENABLE", False)

# ---------------- Topics loader ----------------
def _load_topics() -> list[str]:
    path = _topics_path()
    try:
        if path.exists():
            text = path.read_text(encoding="utf-8")
            data = json.loads(text)
            if isinstance(data, list):
                return [str(x).strip() for x in data if str(x).strip()]
            if isinstance(data, dict):
                # prefer 'topics' or 'questions' keys
                for k in ("topics","questions","items"):
                    if k in data and isinstance(data[k], list):
                        return [str(x).strip() for x in data[k] if str(x).strip()]
    except Exception as e:
        log.warning("[qna-autoask] topics load failed from %s: %s", path, e)
    # fallback minimal pool
    return [
        "Sebutkan satu fakta singkat tentang kopi. Jawab ringkas (≤20 kata).",
        "Berikan 1 tips produktivitas singkat. Maks 1 kalimat.",
        "Apa satu fakta sains acak? Maks 20 kata."
    ]

def _pick_topic() -> str:
    pool = _load_topics()
    try:
        return random.choice(pool)
    except Exception:
        return pool[0]

# ---------------- Cog ----------------
class QnaAutolearnAutoReply(commands.Cog):
    """Seeder QnA: mengirim 'Question by Leina' ke channel isolasi secara berkala.
    Aman untuk runtime: tidak crash meski env belum lengkap; patuh ENABLE setiap tick.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._interval_min = max(_eint("QNA_SEED_INTERVAL_MIN", _eint("QNA_ASK_INTERVAL_MIN", 7)), 1)
        # Loop pakai seconds agar bisa diubah saat runtime
        self.loop.change_interval(minutes=self._interval_min)

    @tasks.loop(seconds=30.0)
    async def loop(self):
        # Gate by runtime enable
        if not _enabled():
            return
        cid = _channel_id()
        if not cid:
            log.warning("[qna-autoask] QNA_CHANNEL_ID not set; skip seeding")
            return

        try:
            await self.bot.wait_until_ready()
            ch = self.bot.get_channel(cid)
            if ch is None:
                # Safe resolve via fetch_channel
                try:
                    ch = await self.bot.fetch_channel(cid)
                except Exception:
                    log.warning("[qna-autoask] channel %s not found; skip", cid)
                    return

            prompt = _pick_topic()
            emb = discord.Embed(title="Question by Leina", description=prompt)
            try:
                emb.set_footer(text="seed:autoreply")
            except Exception:
                pass
            await ch.send(embed=emb)
            log.info("[qna-autoask] seeded question to %s", cid)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("[qna-autoask] loop error")

    async def cog_load(self):
        # Always arm the loop; it will self-gate by ENABLE
        if not self.loop.is_running():
            self.loop.start()
        log.info("[qna-autoask] armed (interval=%s min) enable_runtime=%s chan=%s topics=%s",
                 self._interval_min, _enabled(), _channel_id(), _topics_path())

    async def cog_unload(self):
        try:
            if self.loop.is_running():
                self.loop.cancel()
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(QnaAutolearnAutoReply(bot))
