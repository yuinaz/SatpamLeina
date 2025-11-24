# -*- coding: utf-8 -*-
from __future__ import annotations

from discord.ext import commands

import logging
import discord

from satpambot.bot.modules.discord_bot.helpers.thread_utils import find_thread_by_name, DEFAULT_THREAD_NAME

log = logging.getLogger(__name__)

async def _reuse_if_exists(channel: discord.TextChannel, name: str):
    try:
        th = await find_thread_by_name(channel, name=name)
        if th:
            log.info("[thread_guard] reuse thread: %s (%s)", getattr(th, "name", "?"), getattr(th, "id", "?"))
            return th
    except Exception:
        pass
    return None

def _install_create_wrappers():
    orig_ct = discord.TextChannel.create_thread
    async def create_thread_guard(self: discord.TextChannel, *a, **kw):
        name = kw.get("name") or (a[0] if a else None) or DEFAULT_THREAD_NAME
        reused = await _reuse_if_exists(self, name=name)
        if reused:
            return reused
        return await orig_ct(self, *a, **kw)
    discord.TextChannel.create_thread = create_thread_guard

    if hasattr(discord.Message, "create_thread"):
        orig_mt = discord.Message.create_thread
        async def msg_create_thread_guard(self: discord.Message, *a, **kw):
            name = kw.get("name") or (a[0] if a else None) or DEFAULT_THREAD_NAME
            channel = getattr(self, "channel", None)
            if isinstance(channel, discord.TextChannel):
                reused = await _reuse_if_exists(channel, name=name)
                if reused:
                    return reused
            return await orig_mt(self, *a, **kw)
        discord.Message.create_thread = msg_create_thread_guard

    log.info("[thread_guard] installed create_thread wrappers")

class ThreadCreateGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        _install_create_wrappers()
async def setup(bot: commands.Bot):
    await bot.add_cog(ThreadCreateGuard(bot))