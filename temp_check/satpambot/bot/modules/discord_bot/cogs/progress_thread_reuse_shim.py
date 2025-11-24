# -*- coding: utf-8 -*-
from __future__ import annotations

from discord.ext import commands

import logging, types, asyncio

from satpambot.bot.modules.discord_bot.helpers.thread_utils import ensure_neuro_thread, DEFAULT_THREAD_NAME

log = logging.getLogger(__name__)

class ProgressThreadReuseShim(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        await asyncio.sleep(0.5)
        inst = self.bot.get_cog("LearningProgress")
        if not inst:
            log.info("[reuse_shim] LearningProgress not loaded; nothing to patch")
            return
        orig = getattr(inst, "ensure_thread", None)
        if not orig or not callable(orig):
            log.info("[reuse_shim] no ensure_thread on LearningProgress")
            return

        async def wrapped_ensure_thread():
            th = await ensure_neuro_thread(self.bot, DEFAULT_THREAD_NAME)
            if th:
                log.info("[reuse_shim] reused existing neuro thread: #%s (%s)", getattr(th, "name", "?"), getattr(th, "id", "?"))
                return th
            return await orig()

        inst.ensure_thread = types.MethodType(lambda _self: wrapped_ensure_thread(), inst)
        log.info("[reuse_shim] LearningProgress.ensure_thread patched to reuse by name first")
async def setup(bot: commands.Bot):
    await bot.add_cog(ProgressThreadReuseShim(bot))