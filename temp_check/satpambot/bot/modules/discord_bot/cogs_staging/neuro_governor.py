from __future__ import annotations

# satpambot/bot/modules/discord_bot/cogs/neuro_governor.py
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from satpambot.ai.resource_governor import governor

class NeuroGovernor(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    group = app_commands.Group(name="governor", description="NeuroLite resource governor")

    @group.command(name="status", description="Show current governor status")
    async def status(self, interaction: discord.Interaction):
        s = governor.status()
        embed = discord.Embed(title="NeuroLite Governor", color=0x2ecc71)
        for k, v in s.items():
            embed.add_field(name=k, value=str(v), inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @group.command(name="mode", description="Set governor mode: auto/manual")
    @app_commands.choices(mode=[
        app_commands.Choice(name="auto", value="auto"),
        app_commands.Choice(name="manual", value="manual"),
    ])
    async def set_mode(self, interaction: discord.Interaction, mode: app_commands.Choice[str]):
        governor.set_mode(mode.value)
        await interaction.response.send_message(f"Mode set to **{mode.value}**", ephemeral=True)

    @group.command(name="manual_conc", description="Set manual concurrency (only used in manual mode)")
    async def manual_conc(self, interaction: discord.Interaction, value: app_commands.Range[int, 1, 16]):
        governor.set_manual_conc(int(value))
        await interaction.response.send_message(f"Manual concurrency set to **{value}**", ephemeral=True)

    @group.command(name="thresholds", description="Tune thresholds (CPU low/high, MEM low/high)")
    async def thresholds(self, interaction: discord.Interaction,
                         cpu_low: Optional[float] = None, cpu_high: Optional[float] = None,
                         mem_low: Optional[float] = None, mem_high: Optional[float] = None):
        governor.tune_thresholds(cpu_low, cpu_high, mem_low, mem_high)
        await interaction.response.send_message("Thresholds updated.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(NeuroGovernor(bot))
