from __future__ import annotations

from discord.ext import commands

import logging, time, asyncio
from discord.ext import tasks
from ..helpers import mood_state

log = logging.getLogger(__name__)

class MoodWatcher(commands.Cog):
    """Pantau DB untuk mendeteksi 'learning' dan atur mood (focused/neutral)."""
    def __init__(self, bot):
        self.bot = bot
        self._last_check = 0.0
        self.loop.start()

    def cog_unload(self):
        try: self.loop.cancel()
        except Exception: pass

    @tasks.loop(seconds=45)
    async def loop(self):
        await self.bot.wait_until_ready()
        con = mood_state._open_db()
        try:
            sent, succ, lex = mood_state.counters(con)
            changed = mood_state.update_from_counters(con, sent, succ, lex)
            if not changed:
                # decay: if no learning > 5 min set neutral
                if not mood_state.is_learning_active(300, con):
                    mood_state.set_mood("neutral", con)
        finally:
            con.close()
async def setup(bot):
    await bot.add_cog(MoodWatcher(bot))