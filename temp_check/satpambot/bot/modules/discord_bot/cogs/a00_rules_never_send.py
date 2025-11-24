
# satpambot/bot/modules/discord_bot/cogs/a00_rules_never_send.py
# Hard‑deny kirim ke channel tertentu TANPA tergantung ENV.
# Drop di level Messageable.send → tidak ada kirim dan tidak ada error.

from discord.ext import commands
import discord, logging

log = logging.getLogger(__name__)

# === KONSTAN (EDIT DI SINI SAJA) ===
BLOCK_CHANNEL_IDS = {763793237394718744}
BLOCK_CHANNEL_NAMES = {"rules", "⛔︲rules"}  # dibaca lowercase
DEBUG_DROP_LOG = False  # set True kalau ingin 1-baris log saat drop

class RulesNeverSend(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # simpan original send
        self._orig_send = discord.abc.Messageable.send

        async def _patched_send(target, *args, **kwargs):
            try:
                cid = getattr(target, "id", None)
                name = getattr(target, "name", "")
                lname = (name or "").lower()
                if (cid in BLOCK_CHANNEL_IDS) or (lname in BLOCK_CHANNEL_NAMES):
                    if DEBUG_DROP_LOG:
                        log.info("[rules-never-send] drop send on #%s (id=%s)", name or "?", cid)
                    return None  # silent no-op
            except Exception:
                # Fallback ke perilaku normal bila ada hal tak terduga
                pass
            return await self._orig_send(target, *args, **kwargs)

        # pasang patch
        discord.abc.Messageable.send = _patched_send
        log.info("[rules-never-send] installed (ids=%s, names=%s)",
                 sorted(BLOCK_CHANNEL_IDS), sorted(BLOCK_CHANNEL_NAMES))

    def cog_unload(self):
        # kembalikan original
        discord.abc.Messageable.send = self._orig_send
        log.info("[rules-never-send] uninstalled")
async def setup(bot: commands.Bot):
    await bot.add_cog(RulesNeverSend(bot))