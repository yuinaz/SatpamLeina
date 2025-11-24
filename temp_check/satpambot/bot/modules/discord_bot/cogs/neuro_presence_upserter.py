# -*- coding: utf-8 -*-
"""neuro_presence_upserter.py
Pastikan satu pesan presence pinned di thread neuro: upsert by marker.
"""
from __future__ import annotations

from discord.ext import commands

import os, json, contextlib, logging, asyncio
import discord

log = logging.getLogger(__name__)

NEURO_THREAD_NAME = (os.getenv("NEURO_THREAD_NAME") or "neuro-lite progress").strip()
PRESENCE_MARKER = "presence::keeper"

class NeuroPresenceUpserter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task = None

    async def cog_load(self):
        self._task = asyncio.create_task(self._ensure())

    def cog_unload(self):
        if self._task:
            self._task.cancel()

    async def _ensure(self):
        await self.bot.wait_until_ready()
        # cari thread by name
        for g in self.bot.guilds:
            try:
                for ch in g.text_channels:
                    try:
                        threads = await ch.threads()
                    except Exception:
                        continue
                    for th in threads:
                        if (th.name or "").strip().lower() == NEURO_THREAD_NAME.strip().lower():
                            await self._upsert_to(th)
            except Exception:
                continue

    async def _upsert_to(self, thread: discord.Thread):
        try:
            payload = {
                "status": "online",
                "guild": getattr(thread.guild, "name", None),
                "thread_id": thread.id,
                "thread": thread.name,
            }
            content = f"{PRESENCE_MARKER}\n```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```"
            pinned = await thread.pins()
            keeper = None
            for p in pinned:
                if (p.author == thread.guild.me) and PRESENCE_MARKER in (p.content or ""):
                    keeper = p
                    break
            if keeper:
                await keeper.edit(content=content)
                log.info("[presence_upserter] updated presence keeper")
            else:
                msg = await thread.send(content)
                with contextlib.suppress(Exception):
                    await msg.pin(reason="presence keeper")
                log.info("[presence_upserter] created presence keeper + pinned")
        except Exception as e:
            log.exception("[presence_upserter] failed: %s", e)
async def setup(bot: commands.Bot):
    await bot.add_cog(NeuroPresenceUpserter(bot))