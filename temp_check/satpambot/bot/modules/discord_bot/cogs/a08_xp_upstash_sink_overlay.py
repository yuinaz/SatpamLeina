from discord.ext import commands

import os, json, logging

log = logging.getLogger(__name__)

async def _get_json(url, token, key):
    if not (url and token): return None
    try:
        import aiohttp
        async with aiohttp.ClientSession() as sess:
            r = await sess.get(f"{url}/get/{key}", headers={"Authorization": f"Bearer {token}"}, timeout=8)
            if r.status == 200:
                j = await r.json()
                raw = (j or {}).get("result")
                if not raw:
                    return None
                try:
                    return json.loads(raw)
                except Exception:
                    return None
    except Exception as e:
        log.debug("[xp-upstash-sink] get_json fail: %r", e)
    return None

async def _set_json(url, token, key, obj):
    if not (url and token): return False
    try:
        import aiohttp
        data = json.dumps(obj, ensure_ascii=False)
        async with aiohttp.ClientSession() as sess:
            r = await sess.post(f"{url}/set/{key}/{data}", headers={"Authorization": f"Bearer {token}"}, timeout=8)
            return r.status == 200
    except Exception as e:
        log.debug("[xp-upstash-sink] set_json fail: %r", e)
        return False

class XpUpstashSinkOverlay(commands.Cog):
    """
    Menerima event XP (`on_xp_add`, `on_satpam_xp`) dan menulis total ke store JSON tunggal.
    Format: {"users": {"<uid>": total_int}}
    Toleran: bila key belum ada ➜ dibuat baru.
    """
    def __init__(self, bot):
        self.bot = bot
        self.url = (os.getenv("UPSTASH_REDIS_REST_URL","") or "").rstrip("/") or None
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN") or None
        self.key = os.getenv("UPSTASH_XP_STORE_KEY","xp:bot:users_total")
        log.info("[xp-upstash-sink] ready key=%s url=%s", self.key, "set" if self.url else "none")

    async def _apply_award(self, uid, amt, why=""):
        try:
            uid = str(getattr(uid, "id", uid))  # Member/Int ke str
            amt = int(amt or 0)
        except Exception:
            return
        if not (self.url and self.token):
            return
        data = await _get_json(self.url, self.token, self.key) or {}
        users = data.get("users") or {}
        users[uid] = int(users.get(uid, 0)) + amt
        data["users"] = users
        ok = await _set_json(self.url, self.token, self.key, data)
        if not ok:
            log.debug("[xp-upstash-sink] write failed")

    @commands.Cog.listener()
    async def on_xp_add(self, user_id, amount, reason, *args, **kwargs):
        await self._apply_award(user_id, amount, reason)

    @commands.Cog.listener()
    async def on_satpam_xp(self, user_id, amount, reason, *args, **kwargs):
        await self._apply_award(user_id, amount, reason)

async def setup(bot):
    await bot.add_cog(XpUpstashSinkOverlay(bot))