from __future__ import annotations

from discord.ext import commands

# SPDX-License-Identifier: MIT
# Runtime hook that finds /repo pull_and_restart and wraps its callback to mark a restart sentinel.
import asyncio
from typing import Optional

import discord

from discord import app_commands

from satpambot.bot.modules.discord_bot.helpers import log_utils  # optional, for logging if present
try:
    from satpambot.bot.modules.discord_bot.helpers.restart_sentinel import mark as mark_restart  # type: ignore
except Exception:
    # Fallback import path if this repository is laid out differently
    from .helpers.restart_sentinel import mark as mark_restart  # type: ignore

class RepoRestartHook(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._hooked = False

    async def _find_and_wrap(self) -> None:
        if self._hooked:
            return
        # Give time for other cogs to register their commands
        await asyncio.sleep(1.0)

        target: Optional[app_commands.Command] = None
        for cmd in self.bot.tree.walk_commands():
            # We accept either a top-level command named "repo_pull_and_restart"
            # OR a subcommand named "pull_and_restart" under group "repo"
            if isinstance(cmd, app_commands.Command):
                if cmd.name == "pull_and_restart" and cmd.parent and cmd.parent.name == "repo":
                    target = cmd
                    break
                if cmd.name == "repo_pull_and_restart" and not cmd.parent:
                    target = cmd
                    break

        if not target:
            return  # Nothing to hook

        orig_cb = getattr(target, "_callback", None)
        if not orig_cb:
            return

        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            # Best-effort read "seconds" delay if the command passes it as an option
            seconds = 0.0
            try:
                if interaction.data and isinstance(interaction.data, dict):
                    # options could be nested; keep simple best-effort
                    opts = interaction.data.get("options") or []
                    if isinstance(opts, list):
                        for o in opts:
                            if isinstance(o, dict) and o.get("name") in ("delay", "seconds", "restart_in"):
                                seconds = float(o.get("value") or 0.0)
                                break
            except Exception:
                pass

            # Mark sentinel BEFORE running original logic, so even if the old code exits quickly, we persist the flag.
            try:
                actor = interaction.user.id if interaction.user else None
                mark_restart("pull_and_restart", actor_id=actor, seconds=seconds)
            except Exception:
                pass

            return await orig_cb(interaction, *args, **kwargs)

        # Replace the internal callback (discord.py stores it on _callback)
        setattr(target, "_callback", wrapper)
        self._hooked = True
        try:
            log_utils.info("[repo_restart_hook] Hooked /repo pull_and_restart for restart sentinel.")
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        await self._find_and_wrap()
async def setup(bot: commands.Bot):
    await bot.add_cog(RepoRestartHook(bot))