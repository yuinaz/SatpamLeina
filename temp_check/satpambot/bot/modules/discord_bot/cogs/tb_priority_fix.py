from discord.ext import commands
import asyncio
import logging

log = logging.getLogger(__name__)

def _origin_module(cmd) -> str:
    return getattr(getattr(cmd, "callback", None), "__module__", "") or ""

class TBPriorityFix(commands.Cog):
    """Jaga agar `!tb` aktif berasal dari tb_shim (tanpa operasi agresif yang bikin dobel error)."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self):
        # Tunggu sebentar supaya cogs lain selesai register
        await asyncio.sleep(0.2)
        await self._ensure_shim()

    @commands.Cog.listener()
    async def on_ready(self):
        await self._ensure_shim()

    async def _ensure_shim(self):
        try:
            active_tb = self.bot.get_command("tb")
            if active_tb and _origin_module(active_tb).endswith(".tb_shim"):
                return  # sudah benar
            # Cari tb dari tb_shim (kalau cog-nya sudah terpasang)
            shim_cog = self.bot.cogs.get("TBShimFormatted")
            if not shim_cog:
                return
            for cmd in getattr(shim_cog, "get_commands", lambda: [])():
                if getattr(cmd, "name", "") == "tb":
                    try:
                        # ganti active mapping secara halus
                        self.bot.remove_command("tb")
                    except Exception:
                        pass
                    try:
                        self.bot.add_command(cmd)
                        log.info("[tb_priority_fix] switched tb -> tb_shim")
                    except Exception as e:
                        log.warning("[tb_priority_fix] failed to re-register tb from shim: %s", e)
                    finally:
                        return
        except Exception as e:
            log.debug("[tb_priority_fix] noop due to: %s", e)
async def setup(bot: commands.Bot):
    await bot.add_cog(TBPriorityFix(bot))