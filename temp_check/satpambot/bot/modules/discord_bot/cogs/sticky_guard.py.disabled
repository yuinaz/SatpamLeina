import os, json, time, asyncio, logging, datetime as dt
from zoneinfo import ZoneInfo
import discord
from discord.ext import commands, tasks
from discord import app_commands

log = logging.getLogger("sticky")

STORE = os.getenv("STICKY_STORE", "data/sticky_status.json")
SCAN_LIMIT = int(os.getenv("STICKY_SCAN_LIMIT", "40"))
TITLE = os.getenv("STICKY_TITLE", "SatpamBot Status")

# ===== Timezone & jadwal =====
WIB = ZoneInfo("Asia/Jakarta")
WIB_LABEL = "WIB (UTC+07:00)"     # tampil di footer + field
INTERVAL_MIN = int(os.getenv("STICKY_INTERVAL_MIN", "60"))     # loop tiap 1 jam
STICKY_TTL_MIN = int(os.getenv("STICKY_TTL_MIN", "60"))        # update maksimal 1 jam
STICKY_COOLDOWN_SEC = int(os.getenv("STICKY_COOLDOWN_SEC", "300"))
STICKY_CLEANUP_MIN = int(os.getenv("STICKY_CLEANUP_MIN", "180"))
MAX_DELETE_PER_TICK = int(os.getenv("STICKY_MAX_DELETE", "3"))

def _load():
    try:
        with open(STORE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save(data: dict):
    os.makedirs(os.path.dirname(STORE) or ".", exist_ok=True)
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def _pick_channel(guild: discord.Guild):
    cid_env = os.getenv("STICKY_STATUS_CHANNEL_ID") or os.getenv("STATUS_CHANNEL_ID") or os.getenv("LOG_CHANNEL_ID")
    if cid_env and cid_env.isdigit():
        ch = guild.get_channel(int(cid_env)) or next((c for c in guild.text_channels if c.id == int(cid_env)), None)
        if ch: return ch
    for c in guild.text_channels:
        perms = c.permissions_for(guild.me)
        if perms.send_messages and perms.embed_links:
            return c
    return None

def _embed_payload(bot: commands.Bot, updated_at_unix: int):
    """Bangun payload (hash) + Embed yang menampilkan waktu dalam WIB."""
    user = getattr(bot, "user", None)
    akun = f"{user} (`{user.id}`)" if user else "-"
    presence_text = "`presence=online`"

    # Format WIB eksplisit
    dt_wib = dt.datetime.fromtimestamp(updated_at_unix, tz=WIB)
    fmt_wib = dt_wib.strftime("%Y-%m-%d %H:%M:%S WIB")

    payload = {
        "title": TITLE,
        "akun": akun,
        "presence": presence_text,
        "wib": fmt_wib,
    }

    # Penting: JANGAN pakai timestamp embed bawaan → Discord merender sesuai timezone viewer.
    e = discord.Embed(title=TITLE, color=0x2ecc71)
    e.add_field(name="SatpamBot online dan siap berjaga.", value="\u200b", inline=False)
    e.add_field(name="Akun", value=akun, inline=True)
    e.add_field(name="Presence", value=presence_text, inline=True)
    e.add_field(name="Terakhir diperbarui", value=fmt_wib, inline=False)
    e.add_field(name="Zona waktu", value=WIB_LABEL, inline=True)
    e.set_footer(text=f"SatpamBot Sticky • {WIB_LABEL}")
    return payload, e

def _hash_payload(payload: dict) -> str:
    return "|".join([str(payload.get(k, "")) for k in ("title","akun","presence","wib")])

def _is_ours(msg: discord.Message) -> bool:
    if not msg.author or not msg.author.bot: return False
    if not msg.embeds: return False
    emb = msg.embeds[0]
    title_ok = (emb.title or "").strip() == TITLE
    footer_ok = emb.footer and (emb.footer.text or "").strip().startswith("SatpamBot Sticky")
    return bool(title_ok or footer_ok)

class StickyGuard(commands.Cog):
    """Pastikan status sticky hanya 1 pesan, waktu WIB, hemat rate-limit."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store = _load()
        self._locks: dict[int, asyncio.Lock] = {}
        self.tick.start()

    def cog_unload(self):
        self.tick.cancel()

    def _lock(self, gid: int) -> asyncio.Lock:
        self._locks.setdefault(gid, asyncio.Lock())
        return self._locks[gid]

    @tasks.loop(minutes=INTERVAL_MIN)
    async def tick(self):
        await self.bot.wait_until_ready()
        for g in self.bot.guilds:
            try:
                async with self._lock(g.id):
                    await self._ensure_one(g)
            except Exception:
                log.debug("sticky ensure fail for %s", g.id, exc_info=True)

    @tick.before_loop
    async def before_tick(self):
        await self.bot.wait_until_ready()

    async def _ensure_one(self, guild: discord.Guild):
        ch = _pick_channel(guild)
        if not ch: return

        key = str(guild.id)
        rec = self.store.get(key) or {}
        msg_id = rec.get("message_id")
        last_hash = rec.get("hash", "")
        updated_at = int(rec.get("updated_at") or time.time())
        last_edit_ts = int(rec.get("last_edit_ts") or 0)
        last_cleanup_ts = int(rec.get("last_cleanup_ts") or 0)

        # Ambil pesan eksisting
        msg = None
        if msg_id:
            try: msg = await ch.fetch_message(int(msg_id))
            except Exception: msg = None
        if not msg:
            async for m in ch.history(limit=SCAN_LIMIT):
                if _is_ours(m):
                    msg = m; break

        now = int(time.time())
        payload, embed = _embed_payload(self.bot, updated_at)
        cur_hash = _hash_payload(payload)

        # Update maksimal 1 jam, juga patuhi cooldown kecil untuk jaga-jaga
        should_update = False
        if (now - updated_at) >= STICKY_TTL_MIN*60 and (now - last_edit_ts) >= STICKY_COOLDOWN_SEC:
            updated_at = now
            payload, embed = _embed_payload(self.bot, updated_at)
            new_hash = _hash_payload(payload)
            if new_hash != last_hash:
                cur_hash = new_hash
                should_update = True

        if not msg:
            msg = await ch.send(embed=embed)
            updated_at = now
            cur_hash = _hash_payload(_embed_payload(self.bot, updated_at)[0])
            last_edit_ts = now
        elif should_update:
            try:
                await msg.edit(embed=embed)
                last_edit_ts = now
            except discord.HTTPException as e:
                log.warning("edit sticky failed: %s", e)

        # Cleanup duplikat jarang-jarang
        if (now - last_cleanup_ts) >= STICKY_CLEANUP_MIN*60:
            deleted = 0
            async for m in ch.history(limit=SCAN_LIMIT):
                if m.id == msg.id: continue
                if _is_ours(m):
                    try: await m.delete()
                    except discord.HTTPException: pass
                    deleted += 1
                    if deleted >= MAX_DELETE_PER_TICK: break
                    await asyncio.sleep(0.35)
            last_cleanup_ts = now

        # Simpan state
        self.store[key] = {
            "channel_id": ch.id, "message_id": msg.id, "hash": cur_hash,
            "updated_at": updated_at, "last_edit_ts": last_edit_ts, "last_cleanup_ts": last_cleanup_ts,
        }
        _save(self.store)

    @app_commands.command(name="status-sticky-refresh", description="Perbarui status sticky sekarang (WIB, hemat).")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def sticky_refresh(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        async with self._lock(interaction.guild_id):
            await self._ensure_one(interaction.guild)
        await interaction.followup.send("✅ Sticky status diperbarui.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(StickyGuard(bot))
