from discord.ext import commands
import time, logging
import discord

from ..helpers import health_probe
from ..helpers.upgrade_engine_ext import attempt_rollback_last, last_snapshot
try:
    from ...config import envcfg
except Exception:
    envcfg = None

log = logging.getLogger("satpambot.self_check_boot")

def _resolve_log_channel(bot) -> discord.TextChannel | None:
    ch_id_raw = envcfg.log_channel_id_raw() if envcfg else None
    if ch_id_raw:
        try:
            ch_id = int(ch_id_raw)
            for g in bot.guilds:
                ch = g.get_channel(ch_id)
                if ch: return ch
        except Exception:
            pass
    names = ["log-botphising","log_botphish","bot-log","logs","audit-log"]
    for g in bot.guilds:
        for ch in g.text_channels:
            if (ch.name or "").lower() in names:
                return ch
    return None

class SelfCheckBoot(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not envcfg or not envcfg.boot_dm_online():
            return
        owner_id = envcfg.owner_id() if envcfg else None
        try:
            owner = self.bot.get_user(owner_id) or await self.bot.fetch_user(owner_id)
        except Exception:
            owner = None

        status = health_probe.summarize() if hasattr(health_probe, "summarize") else {}
        ok = all(status.values()) if status else True

        emb = discord.Embed(title="Boot Health Check", colour=0x2ecc71 if ok else 0xe74c3c)
        emb.add_field(name="guard_hooks_has_get_health", value=str(status.get("guard_hooks_has_get_health")), inline=True)
        emb.set_footer(text=f"ts={int(time.time())}")

        if owner:
            try: await owner.send(embed=emb)
            except Exception as e: log.warning("DM owner failed: %s", e)

        if ok: return

        ch = _resolve_log_channel(self.bot)
        if ch and envcfg and envcfg.boot_auto_thread():
            try:
                th = await ch.create_thread(name=f"boot-error-{int(time.time())}", type=discord.ChannelType.public_thread)
            except Exception:
                th = ch
        else:
            th = ch or None

        try:
            if th:
                await th.send(embed=emb)
                snap = last_snapshot()
                if envcfg.boot_auto_rollback() and snap:
                    r = attempt_rollback_last()
                    emb2 = discord.Embed(title="Auto-Rollback", description=f"rollback={'SUCCESS' if r else 'NO-OP'}", colour=0xf1c40f)
                    await th.send(embed=emb2)
        except Exception as e:
            log.warning("thread logging failed: %s", e)
async def setup(bot: commands.Bot):
    await bot.add_cog(SelfCheckBoot(bot))