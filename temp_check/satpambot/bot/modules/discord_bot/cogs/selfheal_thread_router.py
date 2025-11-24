from __future__ import annotations

from discord.ext import commands

# satpambot/bot/modules/discord_bot/cogs/selfheal_thread_router.py
import logging, asyncio
from typing import Optional
import discord

from satpambot.config.runtime import cfg, set_cfg

log = logging.getLogger(__name__)

THREAD_NAME_DEFAULT = "repair and update log"

class SelfhealThreadRouter(commands.Cog):
    """Route send_selfheal() to a dedicated thread under log channel (#log-botphising)."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.thread_id: Optional[int] = None
        self._wrapped = False

    async def cog_load(self):
        await self._ensure_thread_ready()
        await self._wrap_router()

    async def _wrap_router(self):
        if self._wrapped:
            return
        try:
            from .selfheal_router import send_selfheal as _orig
            import satpambot.bot.modules.discord_bot.cogs.selfheal_router as router

            async def _to_thread(bot: commands.Bot, embed: discord.Embed, *a, **k):
                thr = await self._get_thread()
                if thr:
                    try:
                        await thr.send(embed=embed)
                        return
                    except Exception as e:
                        log.warning("[selfheal-thread] send failed, fallback: %s", e)
                # fallback ke original
                return await _orig(bot, embed, *a, **k)

            router.send_selfheal = _to_thread
            self._wrapped = True
            log.info("[selfheal-thread] send_selfheal wrapped to thread")
        except Exception as e:
            log.warning("[selfheal-thread] wrap failed: %s", e)

    async def _ensure_thread_ready(self):
        # try restore from cfg
        tid = cfg("SELFHEAL_THREAD_ID")
        if tid:
            t = self.bot.get_channel(int(tid))
            if isinstance(t, discord.Thread):
                if t.archived:
                    try:
                        await t.edit(archived=False, locked=False)
                    except Exception:
                        pass
                self.thread_id = t.id
                return

        # find log channel by id or by name
        chan = None
        chan_id = cfg("LOG_CHANNEL_ID_RAW") or cfg("LOG_CHANNEL_ID")
        if chan_id:
            chan = self.bot.get_channel(int(chan_id))  # type: ignore
        if chan is None:
            # last resort: cari berdasarkan nama
            target_name = (cfg("LOG_CHANNEL_NAME") or "log-botphising").lower()
            for g in self.bot.guilds:
                for c in g.text_channels:
                    if c.name.lower() == target_name:
                        chan = c; break
                if chan: break

        if not isinstance(chan, discord.TextChannel):
            log.warning("[selfheal-thread] log channel not found; using fallback")
            return

        # ensure a single thread with configured name
        tname = str(cfg("SELFHEAL_THREAD_NAME", THREAD_NAME_DEFAULT))[:80]

        # look for active thread with same name
        for th in chan.threads:
            if th.name == tname:
                self.thread_id = th.id
                set_cfg("SELFHEAL_THREAD_ID", th.id)
                return

        # create a fresh thread from an anchor message
        try:
            anchor = await chan.send("Self-heal: thread anchor")
            th = await anchor.create_thread(name=tname, auto_archive_duration=10080)  # 7 days
            self.thread_id = th.id
            set_cfg("SELFHEAL_THREAD_ID", th.id)
            log.info("[selfheal-thread] created thread '%s' (id=%s)", tname, th.id)
        except Exception as e:
            log.warning("[selfheal-thread] failed to create thread: %s", e)

    async def _get_thread(self) -> Optional[discord.Thread]:
        if self.thread_id:
            ch = self.bot.get_channel(int(self.thread_id))
            if isinstance(ch, discord.Thread):
                return ch
        await self._ensure_thread_ready()
        if self.thread_id:
            ch = self.bot.get_channel(int(self.thread_id))
            if isinstance(ch, discord.Thread):
                return ch
        return None
async def setup(bot: commands.Bot):
    await bot.add_cog(SelfhealThreadRouter(bot))