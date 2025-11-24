from discord.ext import commands
import os, logging, asyncio, time
import discord

try:
    import httpx
except Exception:
    httpx = None

log = logging.getLogger(__name__)

# ENV
ENABLE = os.getenv("GATE_ENABLE", "1") == "1"
MOD_CHANNELS = {int(x) for x in (os.getenv("GATE_MOD_CHANNEL_IDS","").split(",") if os.getenv("GATE_MOD_CHANNEL_IDS") else []) if x.strip().isdigit()}
ALLOW_USER_IDS = {int(x) for x in (os.getenv("GATE_ALLOW_USER_IDS","").split(",") if os.getenv("GATE_ALLOW_USER_IDS") else []) if x.strip().isdigit()}
UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")
GATE_KEY = os.getenv("QNA_PUBLIC_GATE_KEY", "qna:public:enable")

async def _upstash_set(key, val):
    if not (UPSTASH_URL and UPSTASH_TOKEN and httpx):
        return False
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{UPSTASH_URL}/set/{key}/{val}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}, timeout=6.0)
            return r.status_code == 200
    except Exception:
        return False

async def _upstash_get(key):
    if not (UPSTASH_URL and UPSTASH_TOKEN and httpx):
        return None
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{UPSTASH_URL}/get/{key}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}, timeout=6.0)
            if r.status_code == 200:
                return (r.json() or {}).get("result")
    except Exception:
        return None

def _is_mod_ctx(ctx: commands.Context) -> bool:
    if ctx.guild is None:
        # DM context — only allow ALLOW_USER_IDS (no spam to owner)
        return ctx.author.id in ALLOW_USER_IDS if ALLOW_USER_IDS else True
    if MOD_CHANNELS and ctx.channel.id not in MOD_CHANNELS:
        return False
    # allow if admin/mod or explicit allowlist
    if ctx.author.id in ALLOW_USER_IDS:
        return True
    perms = ctx.author.guild_permissions
    return perms.administrator or perms.manage_guild or perms.manage_messages

class GateControl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        log.info("[gate] control loaded (enable=%s, mod_channels=%s, allow_users=%s)",
                 ENABLE, sorted(MOD_CHANNELS) if MOD_CHANNELS else "any", sorted(ALLOW_USER_IDS) if ALLOW_USER_IDS else "any")

    @commands.command(name="gate")
    async def gate(self, ctx: commands.Context, action: str=None):
        if not ENABLE:
            return
        if not _is_mod_ctx(ctx):
            return
        action = (action or "").lower().strip()
        if action not in {"unlock","lock","status"}:
            await ctx.reply("Usage: `!gate unlock|lock|status`", mention_author=False)
            return
        if action == "status":
            val = await _upstash_get(GATE_KEY)
            state = "ON" if str(val) == "1" else "OFF"
            await ctx.reply(f"[gate] QnA public is **{state}**", mention_author=False)
            return
        target = "1" if action == "unlock" else "0"
        ok = await _upstash_set(GATE_KEY, target)
        if ok:
            await ctx.reply(f"[gate] QnA public -> **{'ON' if target=='1' else 'OFF'}**", mention_author=False)
        else:
            await ctx.reply("[gate] failed (storage not configured)", mention_author=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(GateControl(bot))
