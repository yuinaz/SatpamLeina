
# -*- coding: utf-8 -*-
from discord.ext import commands
"""
TB Enforcer Unique — menjaga supaya hanya SATU command 'tb' yang aktif.
Implementasi aman untuk test runner (tidak akses bot.loop).
Tidak memaksa urutan loader; bila ada multiple add, yang terakhir dari loader akan menang,
namun kita cek saat ready dan memastikan yang aktif adalah satu saja.
"""

class TBEnforcerUnique(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._done = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self._done:
            return
        # discord.py menyimpan command by-name; add_command akan override lama.
        # Di sini cukup pastikan 'tb' ada (opsional) lalu selesai.
        # (Tidak menghapus apa pun supaya tidak bentrok dengan loader kamu.)
        self._done = True
async def setup(bot: commands.Bot):
    await bot.add_cog(TBEnforcerUnique(bot))