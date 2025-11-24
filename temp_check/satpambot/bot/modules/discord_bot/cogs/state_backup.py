from discord.ext import commands
import io, logging, os

from discord.ext import tasks

log = logging.getLogger(__name__)

FILES_TO_BACKUP = [
    "data/env_vault.json",
    "data/phrasebook.json",
    "data/personality.json",
    "data/sticker_learner.sqlite3",
]

class StateBackup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.enabled = False  # default off

    @tasks.loop(hours=24)
    async def _backup_loop(self):
        if not self.enabled:
            return
        buf = io.BytesIO()
        txt = []
        for p in FILES_TO_BACKUP:
            if os.path.exists(p):
                try:
                    txt.append(f"## {p}\n" + open(p,'r',encoding='utf-8', errors='ignore').read()[:4000])
                except Exception:
                    pass
        buf.write(("\n\n".join(txt)).encode("utf-8"))
        buf.seek(0)
        log.info("[backup] state snapshot prepared (%d bytes)", buf.getbuffer().nbytes)

    async def cog_load(self):
        self._backup_loop.start()

    async def cog_unload(self):
        self._backup_loop.cancel()
async def setup(bot):
    await bot.add_cog(StateBackup(bot))