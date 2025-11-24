from __future__ import annotations

from discord.ext import commands

import os

from ..helpers import env_store

class EnvImportAll(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="env", invoke_without_command=True)
    async def env_root(self, ctx: commands.Context):
        await ctx.reply("env import-all | env set KEY VALUE | env get KEY", mention_author=False)

    @env_root.command(name="import-all")
    async def env_import_all(self, ctx: commands.Context):
        n = 0
        for k, v in os.environ.items():
            env_store.set(k, v, source="import-cmd")
            n += 1
        await ctx.reply(f"Imported {n} env keys into DB.", mention_author=False)

    @env_root.command(name="set")
    async def env_set(self, ctx: commands.Context, key: str, *, value: str):
        env_store.set(key, value, source="cmd")
        await ctx.reply(f"ENV {key} set.", mention_author=False)

    @env_root.command(name="get")
    async def env_get(self, ctx: commands.Context, key: str):
        v = env_store.get(key)
        await ctx.reply(f"{key} = {v!r}", mention_author=False)
async def setup(bot):
    await bot.add_cog(EnvImportAll(bot))