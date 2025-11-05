# satpambot/bot/modules/discord_bot/shim_runner.py
import os, logging, discord, sys
from discord.ext import commands

# ========= util: env normalizer (.env loader + alias token) =========
def _load_dotenv_light():
    # cari .env di beberapa lokasi umum (root repo / cwd)
    candidates = [
        os.path.join(os.getcwd(), ".env"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env")),
    ]
    for path in candidates:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'").strip('"')
                    os.environ.setdefault(k, v)
        except Exception:
            pass

def _normalize_env():
    # coba pakai preflight kalau ada
    try:
        from scripts import preflight_render_free as _preflight
        _preflight.run()
        return
    except Exception:
        pass

    # fallback lokal
    _load_dotenv_light()

    # alias nama2 token → DISCORD_TOKEN + mirror ke DISCORD_BOT_TOKEN
    synonyms = [
        "DISCORD_TOKEN",
        "DISCORD_BOT_TOKEN",
        "BOT_TOKEN",
        "discord_bot_token",
        "discord_token",
        "token",
    ]
    val = None
    for name in synonyms:
        v = os.getenv(name)
        if v:
            val = v
            break
    if val and not os.getenv("DISCORD_TOKEN"):
        os.environ["DISCORD_TOKEN"] = val
    if os.getenv("DISCORD_TOKEN") and not os.getenv("DISCORD_BOT_TOKEN"):
        os.environ["DISCORD_BOT_TOKEN"] = os.environ["DISCORD_TOKEN"]

    # alias untuk gemini bila user hanya set GOOGLE_API_KEY
    if not os.getenv("GEMINI_API_KEY") and os.getenv("GOOGLE_API_KEY"):
        os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY")

def _get_token() -> str | None:
    return (
        os.getenv("DISCORD_TOKEN")
        or os.getenv("DISCORD_BOT_TOKEN")
        or os.getenv("BOT_TOKEN")
        or os.getenv("discord_bot_token")
        or os.getenv("discord_token")
        or os.getenv("token")
    )

# ========= cogs loader =========
try:
    from .cogs_loader import load_cogs
except Exception:
    from satpambot.bot.modules.discord_bot.cogs_loader import load_cogs  # type: ignore

log = logging.getLogger(__name__)

# ===== Intents =====
intents = discord.Intents.default()
intents.guilds = True
intents.members = True     # required for some moderation checks & metrics online count
intents.presences = True   # metrics online count
intents.message_content = True  # ensure enabled in Discord Dev Portal

PREFIX = os.getenv("COMMAND_PREFIX", "!")
allowed_mentions = discord.AllowedMentions(
    everyone=False, users=True, roles=False, replied_user=False
)

bot = commands.Bot(command_prefix=PREFIX, intents=intents, allowed_mentions=allowed_mentions)

# ===== Events =====
@bot.event
async def on_ready():
    try:
        from satpambot.bot.modules.discord_bot.helpers import log_utils
    except Exception:
        log_utils = None  # type: ignore

    import time
    if not getattr(bot, "start_time", None):
        bot.start_time = time.time()
    try:
        if log_utils:
            for g in list(getattr(bot, "guilds", []) or []):
                log_utils.log_startup_status(bot, g)
    except Exception:
        pass
    try:
        log.info("✅ Bot login as %s (%s)", bot.user, bot.user.id if bot.user else "?")
    except Exception:
        log.info("✅ Bot login.")

@bot.event
async def setup_hook():
    # muat semua cogs default via loader
    try:
        await load_cogs(bot)
    except Exception as e:
        log.error("Failed to load cogs: %s", e, exc_info=True)

    # === Tambahan: pastikan live_metrics_push ter-load ===
    # Bisa dimatikan dengan METRICS_DISABLE=1
    if os.getenv("METRICS_DISABLE", "0") not in ("1", "true", "TRUE"):
        ext = "satpambot.bot.modules.discord_bot.cogs.live_metrics_push"
        try:
            if ext not in bot.extensions:
                await bot.load_extension(ext)
                log.info("✅ Loaded metrics cog: %s", ext)
            else:
                log.info("ℹ️ Metrics cog already loaded: %s", ext)
        except Exception as e:
            log.error("⚠️ Could not load metrics cog (%s): %s", ext, e, exc_info=True)

# ===== Entrypoint =====
async def start_bot():
    # penting: normalisasi env sebelum baca token
    _normalize_env()
    token = _get_token()
    if not token:
        raise RuntimeError("ENV DISCORD_TOKEN / DISCORD_BOT_TOKEN / BOT_TOKEN tidak diset")
    await bot.start(token)

# ===== Bridge bot -> dashboard (opsional) =====
try:
    from satpambot.dashboard.discord_bridge import set_bot as _dash_set_bot
    _dash_set_bot(bot)
except Exception:
    pass
