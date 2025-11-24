# -*- coding: utf-8 -*-
"""IntentsProbe (quiet in smoke/test; strict in real Bot)
- Downgrade noisy ERROR during unit/smoke (non-commands.Bot) to INFO.
- Keep a WARNING in real Bot runtime if message_content is disabled.
"""
from __future__ import annotations

from discord.ext import commands

import logging
from typing import Any

try:
    import discord

except Exception:  # pragma: no cover
    discord = None  # type: ignore
    commands = None  # type: ignore

log = logging.getLogger(__name__)

class IntentsProbe:
    def __init__(self, bot: Any) -> None:
        self.bot = bot
        self._run_probe()

    def _run_probe(self) -> None:
        # If discord/commands not available, nothing to probe.
        if discord is None or commands is None:
            log.info("[intents-probe] discord not available; skipped (smoke/test env).")
            return

        is_real_bot = isinstance(self.bot, (commands.Bot, getattr(commands, "AutoShardedBot", ())))
        intents = getattr(self.bot, "intents", None)

        # No intents attribute or wrong type -> in smoke env treat as INFO; in real bot warn once.
        if intents is None or not isinstance(intents, discord.Intents):
            if is_real_bot:
                log.warning("[intents-probe] bot.intents tidak tersedia/valid. "
                            "Gunakan discord.Intents.default() lalu set message_content=True.")
            else:
                log.info("[intents-probe] skipped: bot tanpa .intents (kemungkinan smoke/test env).")
            return

        # We have Intents: ensure message_content enabled
        if not getattr(intents, "message_content", False):
            level = logging.WARNING if is_real_bot else logging.INFO
            log.log(level, "[intents-probe] message_content=False. Aktifkan di Developer Portal dan di code: "
                           "Intents.message_content = True")
        else:
            log.debug("[intents-probe] OK (message_content=True).")
async def setup(bot: Any) -> None:
    # Cogs-less utility; just run the probe on setup.
    IntentsProbe(bot)