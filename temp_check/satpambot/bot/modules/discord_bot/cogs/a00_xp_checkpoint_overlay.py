from discord.ext import commands

import os
import re
import asyncio
import logging

# Abstraksi store yang memilih Postgres (jika tersedia) atau JSON
from satpambot.bot.utils import xp_store as store

# Konfigurasi bonus reset via ENV (default 1000 untuk TK & SD)
BONUS_TK = int(os.getenv("XP_RESET_BONUS_TK", "1000"))
BONUS_SD = int(os.getenv("XP_RESET_BONUS_SD", "1000"))
BONUS_DEFAULT = int(os.getenv("XP_RESET_BONUS_DEFAULT", "0"))

RE_XP = re.compile(r"\[passive-learning\]\s*\+(\d+)\s*XP\s*->\s*total=(\d+)\s*level=([A-Za-z0-9_-]+)")

_LOGGER_NAME = "satpambot.bot.modules.discord_bot.cogs.learning_passive_observer"
log = logging.getLogger(__name__)

class XPCheckpointOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._handler = None
        self._last_total = None  # shadow state for detecting drops

    @commands.Cog.listener()
    async def on_ready(self):
        # Restore terakhir dari store
        try:
            total, level = await store.load("global")
            self._last_total = total
        except Exception as e:
            log.warning("[xp] load failed: %r", e)
            total, level = None, None

        if total is not None:
            await self._apply_restore(total, level)

        # Tap logger hanya sekali
        if not self._handler:
            self._handler = self._make_handler()
            src_logger = logging.getLogger(_LOGGER_NAME)
            src_logger.addHandler(self._handler)

    async def _apply_restore(self, total: int, level: str):
        """Coba restore ke modul passive-learning tanpa menurunkan angka."""
        try:
            import satpambot.bot.modules.discord_bot.cogs.learning_passive_observer as lpo  # type: ignore
        except Exception:
            log.exception("[xp] restore failed (import)")
            return

        try:
            # Prefer setter resmi bila tersedia
            if hasattr(lpo, "set_total_from_checkpoint"):
                maybe = lpo.set_total_from_checkpoint(total, level)
                if asyncio.iscoroutine(maybe):
                    await maybe
                log.info("[xp] restored via setter total=%s level=%s", total, level)
                return

            # Fallback: naikkan global vars jika ada, tanpa pernah menurunkan
            cur = getattr(lpo, "TOTAL_XP", 0)
            if isinstance(cur, (int, float)) and total > cur:
                setattr(lpo, "TOTAL_XP", int(total))
                setattr(lpo, "LEVEL", level or getattr(lpo, "LEVEL", "TK"))
                log.info("[xp] restored fallback total=%s level=%s", total, level)
        except Exception:
            log.exception("[xp] restore failed")

    def _make_handler(self):
        overlay = self
        class _H(logging.Handler):
            def emit(inner, record):
                msg = record.getMessage()
                m = RE_XP.search(msg)
                if not m:
                    return
                try:
                    gain = int(m.group(1))
                    total = int(m.group(2))
                    level = m.group(3)

                    prev = overlay._last_total

                    # Deteksi reset: total turun
                    if prev is not None and total < prev:
                        bonus = BONUS_TK if level.upper() == "TK" else BONUS_SD if level.upper() == "SD" else BONUS_DEFAULT
                        corrected = max(prev, total) + bonus
                        log.warning("[xp] RESET detected: prev=%s now=%s level=%s -> applying bonus +%s => %s",
                                    prev, total, level, bonus, corrected)
                        overlay._last_total = corrected
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(store.save(corrected, level, "global"))
                            loop.create_task(overlay._apply_restore(corrected, level))
                        except RuntimeError:
                            pass
                        return

                    # Normal path: persist total terbaru
                    overlay._last_total = total
                    try:
                        asyncio.get_running_loop().create_task(store.save(total, level, "global"))
                    except RuntimeError:
                        pass

                except Exception:
                    log.exception("[xp] tap failed")

        h = _H()
        h.setLevel(logging.INFO)
        return h

async def setup(bot):
    await bot.add_cog(XPCheckpointOverlay(bot))