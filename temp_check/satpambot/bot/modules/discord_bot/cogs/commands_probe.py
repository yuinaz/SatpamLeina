from __future__ import annotations

from discord.ext import commands

import logging

log = logging.getLogger("commands_probe")

class CommandsProbe(commands.Cog):
    """Logs the list of registered prefix & slash commands after sync."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._done = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self._done:
            return
        self._done = True
        try:
            # Collect prefix commands
            prefix_cmds = sorted([c.name for c in self.bot.commands])
            # Collect slash (app) commands
            tree_cmds = []
            try:
                for g in self.bot.guilds:
                    cmds = await self.bot.tree.fetch_commands(guild=g)
                    tree_cmds.extend([f"{c.name}@{g.name}" for c in cmds])
            except Exception:
                # Fallback: global list (may be stale)
                tree_cmds = [c.name for c in await self.bot.tree.fetch_commands()]
            log.info("[probe] prefix=%s", ", ".join(prefix_cmds))
            log.info("[probe] slash=%s", ", ".join(sorted(tree_cmds)))
        except Exception as e:
            log.warning("[probe] failed: %s", e)
async def setup(bot: commands.Bot):
    await bot.add_cog(CommandsProbe(bot))