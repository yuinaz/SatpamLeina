
# a00_prefer_upstash_bootstrap.py
# Force "Upstash as source of truth" for XP at boot and align pinned snapshot.
from discord.ext import commands
import asyncio, json, os, numbers

try:
    import httpx
except Exception:
    httpx = None

# cfg() helper (falls back to env when not available)
try:
    from satpambot.config.runtime import cfg
    def _cfg(k, default=None):
        try:
            v = cfg(k)
            return default if v in (None, "") else v
        except Exception:
            return os.getenv(k, default)
except Exception:
    def _cfg(k, default=None):
        return os.getenv(k, default)

UPSTASH_URL   = _cfg("UPSTASH_REDIS_REST_URL")
UPSTASH_TOKEN = _cfg("UPSTASH_REDIS_REST_TOKEN")

# Default keys follow user's established naming
_DEFAULT_KEYS = {"senior_total":"xp:bot:senior_total","tk_total":"xp:bottk_total","phase":"learning:phase"}
try:
    XP_KEYS = json.loads(_cfg("XP_UPSTASH_BOT_KEYS_JSON", json.dumps(_DEFAULT_KEYS)))
except Exception:
    XP_KEYS = _DEFAULT_KEYS

PREFERRED_PHASE = _cfg("XP_UPSTASH_PREFERRED_PHASE", None)  # e.g., "senior"
# Thread used by your progress relay / pinned "XP: Miner Memory"
def _to_intish(val):
    if val is None:
        return 0
    if isinstance(val, numbers.Number):
        return int(val)
    if isinstance(val, (bytes, bytearray)):
        try:
            val = val.decode("utf-8", "ignore")
        except Exception:
            val = str(val)
    if isinstance(val, str):
        s = val.strip().strip('"').strip("'")
        # direct integer?
        try:
            return int(s)
        except Exception:
            pass
        # maybe JSON like {"senior_total_xp": 2691}
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                for k in ("senior_total_xp","senior_total","total","value","xp","count"):
                    if k in obj and isinstance(obj[k], numbers.Number):
                        return int(obj[k])
            if isinstance(obj, list) and obj and isinstance(obj[0], numbers.Number):
                return int(obj[0])
        except Exception:
            pass
    # fallback
    try:
        return int(str(val))
    except Exception:
        return 0

def _to_phase(val):
    if val is None:
        return None
    if isinstance(val, (bytes, bytearray)):
        try:
            val = val.decode("utf-8", "ignore")
        except Exception:
            val = str(val)
    if isinstance(val, str):
        s = val.strip().strip('"').strip("'")
        # JSON object carrying phase?
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                for k in ("phase","learning_phase","track","value"):
                    v = obj.get(k)
                    if isinstance(v, str) and v:
                        return v
            if isinstance(obj, str) and obj:
                return obj
        except Exception:
            pass
        return s or None
    return str(val)

try:
    PREFERRED_THREAD_ID = int(_cfg("XP_PINNED_THREAD_ID", "1426397317598154844"))
except Exception:
    PREFERRED_THREAD_ID = None

async def _upstash_get(client, key: str):
    r = await client.get(f"{UPSTASH_URL}/get/{key}")
    r.raise_for_status()
    data = r.json()
    return (data or {}).get("result")

async def _fetch_state_from_upstash():
    if not (UPSTASH_URL and UPSTASH_TOKEN and httpx):
        return None
    headers = {"Authorization": f"Bearer {UPSTASH_TOKEN}"}
    async with httpx.AsyncClient(timeout=10, headers=headers) as client:
        senior = await _upstash_get(client, XP_KEYS["senior_total"])
        tk     = await _upstash_get(client, XP_KEYS["tk_total"])
        phase  = await _upstash_get(client, XP_KEYS["phase"])
        return {
            "senior_total": _to_intish(senior),
            "tk_total": _to_intish(tk),
            "phase": (PREFERRED_PHASE or _to_phase(phase) or "TK-L1")
        }

class PreferUpstashBootstrap(commands.Cog):
    """Override any pinned checkpoint with Upstash totals and keep pinned snapshot in sync."""
    def __init__(self, bot):
        self.bot = bot

    async def on_ready_do(self):
        # Let other cogs settle (e.g., pinned checkpoint), then override from Upstash
        await asyncio.sleep(3.0)
        state = await _fetch_state_from_upstash()
        if not state:
            return

        # 1) Broadcast internal event with absolute state so other bridges can align
        try:
            # Prefer a specific custom event name function to avoid signature issues
            self.bot.dispatch("satpam_xp_set_global", state)
        except Exception:
            pass

        # 2) Align pinned "XP: Miner Memory" snapshot (visual/anchor)
        if PREFERRED_THREAD_ID:
            try:
                from satpambot.bot.modules.discord_bot.helpers.memory_upsert import upsert_pinned_memory
                payload = {
                    "channel_id": PREFERRED_THREAD_ID,
                    "title": "XP: Miner Memory",
                    "content": (
                        f"**Phase:** {state['phase']}\n"
                        f"**Senior Total:** {state['senior_total']}\n"
                        f"**TK Total:** {state['tk_total']}\n"
                        f"_Source: Upstash (authoritative)_"
                    ),
                    "markers": ["xp", "upstash", "authoritative"],
                }
                await upsert_pinned_memory(self.bot, payload)
            except Exception:
                # Non-fatal; XP logic still aligned with Upstash
                pass

    @commands.Cog.listener()
    async def on_ready(self):
        url = UPSTASH_URL
        token = UPSTASH_TOKEN
        if not (url and token):
            return
        # Launch task
        try:
            asyncio.create_task(self.on_ready_do())
        except Exception:
            pass
async def setup(bot):
    await bot.add_cog(PreferUpstashBootstrap(bot))