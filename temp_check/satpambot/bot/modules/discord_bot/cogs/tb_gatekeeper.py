
# -*- coding: utf-8 -*-
from discord.ext import commands
"""
TB Gatekeeper — versi ringan.
Tujuan: Tidak memblok !tb meski command ban belum ada.
Hanya log sekali di console kalau ban/tempban/tban tidak ditemukan.
"""
import logging

log = logging.getLogger("tb_gatekeeper")

class TBGatekeeperPreferShim(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._warned = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self._warned:
            return
        names = set(self.bot.all_commands.keys())
        if not any(n in names for n in ("ban", "tban", "tempban")):
            log.warning("tb_gatekeeper: target ban command tidak ditemukan (ban/tban/tempban). "
                        "Hanya log; !tb tetap diizinkan.")
        self._warned = True
async def setup(bot: commands.Bot):
    await bot.add_cog(TBGatekeeperPreferShim(bot))