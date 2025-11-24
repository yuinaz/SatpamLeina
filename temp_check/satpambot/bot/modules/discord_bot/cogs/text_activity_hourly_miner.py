
# text_activity_hourly_miner.py
# Miner ringan untuk pesan teks umum; snapshot ke JSON agar pengetahuan bertambah
from discord.ext import commands
import asyncio, json, os, time, logging
from discord.ext import tasks

log = logging.getLogger(__name__)

# Tuning default (disamakan dengan overlay)
TEXT_PER_CHANNEL_LIMIT = 100
TEXT_TOTAL_BUDGET      = 900
TEXT_PAGINATE_LIMIT    = 100
TEXT_MIN_SLEEP_SECONDS = 0.80
TEXT_SKIP_CHANNEL_IDS = {
    763813761814495252, 936689852546678885, 767401659390623835, 1270611643964850178,
    761163966482743307, 1422084695692414996, 1372983711771001064, 1378739739930398811,
}

STATE_FILE = "data/neuro-lite/text_miner_state.json"   # cursor per channel (last_id)
SNAPSHOT_FILE = "data/neuro-lite/text_miner_snapshot.json"  # ringkasan mentah

def _ensure_dir(path):
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def _read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as r:
            return json.load(r)
    except Exception:
        return default

def _atomic_write(path, obj):
    _ensure_dir(path)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as w:
        json.dump(obj, w, ensure_ascii=False, indent=2)
        w.flush()
        os.fsync(w.fileno())
    os.replace(tmp, path)

class TextActivityMiner(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.loop_delay = int(os.getenv("TEXT_MINER_DELAY_SEC", "360"))  # start delay agar tidak nabrak startup
        self.every_sec = int(os.getenv("TEXT_MINER_INTERVAL_SEC", "3600"))
        self.job.change_interval(seconds=self.every_sec)
        self.job.start()
    
    def cog_unload(self):
        self.job.cancel()
    
    @tasks.loop(seconds=3600)
    async def job(self):
        await asyncio.sleep(self.loop_delay)
        # muat state
        state = _read_json(STATE_FILE, {})
        snapshot = _read_json(SNAPSHOT_FILE, {"items": [], "ts": int(time.time())})
        processed_total = 0
        gchs = []
        # kumpulkan text channel dari guilds
        for g in self.bot.guilds:
            for ch in getattr(g, "text_channels", []):
                gchs.append(ch)
        # iterasi channel
        for ch in gchs:
            if ch.id in TEXT_SKIP_CHANNEL_IDS:
                continue
            last_id = state.get(str(ch.id))
            limit_ch = 0
            try:
                async for msg in ch.history(limit=TEXT_PAGINATE_LIMIT, after=None, oldest_first=False, before=None):
                    # stop kalau sudah melewati batas terakhir yang tersimpan
                    if last_id and msg.id <= last_id:
                        break
                    # ambil hanya pesan teks biasa
                    if msg.author.bot:
                        continue
                    if not msg.content or not msg.content.strip():
                        continue
                    snapshot["items"].append({
                        "guild": getattr(ch.guild, "name", "?"),
                        "channel": getattr(ch, "name", str(ch.id)),
                        "channel_id": ch.id,
                        "author_id": msg.author.id,
                        "author": str(msg.author),
                        "id": msg.id,
                        "ts": int(msg.created_at.timestamp()) if getattr(msg, "created_at", None) else int(time.time()),
                        "content": msg.content[:1500],
                        "url": msg.jump_url,
                    })
                    limit_ch += 1
                    processed_total += 1
                    state[str(ch.id)] = max(msg.id, state.get(str(ch.id), 0))
                    if limit_ch >= TEXT_PER_CHANNEL_LIMIT:
                        break
                    if processed_total >= TEXT_TOTAL_BUDGET:
                        break
                    await asyncio.sleep(TEXT_MIN_SLEEP_SECONDS)
            except Exception as e:
                log.debug("[text_miner] skip channel %s: %r", ch, e)
            if processed_total >= TEXT_TOTAL_BUDGET:
                break
        snapshot["ts"] = int(time.time())
        # simpan snapshot & state atomik
        try:
            _atomic_write(SNAPSHOT_FILE, snapshot)
            _atomic_write(STATE_FILE, state)
            log.info("[text_miner] snapshot items=%s (per_channel=%s total_budget=%s)", 
                        len(snapshot.get("items", [])), TEXT_PER_CHANNEL_LIMIT, TEXT_TOTAL_BUDGET)
        except Exception as e:
            log.warning("[text_miner] gagal simpan snapshot/state: %r", e)
    
    @job.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()
async def setup(bot):
    await bot.add_cog(TextActivityMiner(bot))