from __future__ import annotations

from discord.ext import commands

import shutil, platform
try:
    import psutil
except Exception:
    psutil = None
import discord
from discord.ext import tasks
from .selfheal_router import send_selfheal

def _mk_embed(title: str, desc: str, color: int):
    return discord.Embed(title=title, description=desc, color=color)

def _percent_bar(pct: float, width: int = 16) -> str:
    pct = max(0.0, min(100.0, pct)); filled = int(round((pct/100.0)*width))
    return '█'*filled + '░'*(width-filled)

class ResourceMonitor(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if hasattr(self, 'loop'): self.loop.start()  # type: ignore

    def _snapshot(self):
        cpu = float(psutil.cpu_percent(interval=0.2)) if psutil else 0.0
        vm = psutil.virtual_memory() if psutil else None
        mem_pct = float(vm.percent) if vm else 0.0
        total, used, free = shutil.disk_usage('/')
        disk_pct = (used/total)*100.0 if total else 0.0
        return cpu, mem_pct, disk_pct

    @tasks.loop(minutes=10)
    async def loop(self):
        cpu, mem, disk = self._snapshot()
        host = platform.node()
        em = _mk_embed('Periodic Status', f'Host: `{host}`', 0x3498db)
        em.add_field(name='CPU', value=f'{cpu:.1f}%  {_percent_bar(cpu)}', inline=True)
        em.add_field(name='Mem', value=f'{mem:.1f}%  {_percent_bar(mem)}', inline=True)
        em.add_field(name='Disk', value=f'{disk:.1f}%  {_percent_bar(disk)}', inline=True)
        await send_selfheal(self.bot, em)
async def setup(bot): await bot.add_cog(ResourceMonitor(bot))