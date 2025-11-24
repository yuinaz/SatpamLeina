
# hot_env_reload.py — safe async reload for discord.py variants
# - Watches SatpamBot.env (or custom path via SATPAMBOT_ENV_FILE) and reloads all extensions on change.
# - Supports both sync/async reload_extension API via reload_extensions_safely helper.
# - Gracefully disables itself if SATPAMBOT_ENV_FILE is set to /dev/null (Linux) or NUL (Windows) or HOTENV_ENABLE=0.
# - Warns at most once if the env file is missing (prevents log spam).

from discord.ext import commands
import os
import asyncio
import logging
from typing import List
from discord.ext import tasks

from satpambot.bot.modules.discord_bot.helpers.hotenv_reload_helpers import reload_extensions_safely

log = logging.getLogger(__name__)

def _is_disabled_path(p: str | None) -> bool:
    if not p:
        return False
    pl = str(p).strip().lower()
    return pl in {"nul", "/dev/null", "null"}

class HotEnvReload(commands.Cog):
    def __init__(self, bot: commands.Bot, env_path: str | None = None, interval_seconds: float = 2.0):
        self.bot = bot
        self.env_path = env_path or os.environ.get("SATPAMBOT_ENV_FILE", "SatpamBot.env")
        self.interval_seconds = interval_seconds
        self._last_mtime: float | None = None
        self._missing_warned: bool = False
        self._disabled: bool = _is_disabled_path(self.env_path) or os.environ.get("HOTENV_ENABLE", "1") in {"0", "false", "False"}

        if self._disabled:
            log.info("[hotenv] disabled (env: SATPAMBOT_ENV_FILE=%s, HOTENV_ENABLE=%s)",
                     self.env_path, os.environ.get("HOTENV_ENABLE", "1"))
            return

        log.info("[hotenv] watching env file: %s (interval=%.2fs)", self.env_path, self.interval_seconds)
        self._watch.start()

    def cog_unload(self):
        try:
            self._watch.cancel()
        except Exception:
            pass

    @tasks.loop(seconds=2.0)
    async def _watch(self):
        if self._watch.seconds != self.interval_seconds:
            self._watch.change_interval(seconds=self.interval_seconds)

        try:
            st = os.stat(self.env_path)
        except FileNotFoundError:
            if not self._missing_warned:
                log.warning("[hotenv] env file not found: %s", self.env_path)
                self._missing_warned = True
            await asyncio.sleep(0)
            return
        except Exception:
            log.exception("[hotenv] failed to stat env file: %s", self.env_path)
            return

        if self._missing_warned:
            self._missing_warned = False

        mtime = st.st_mtime
        if self._last_mtime is None:
            self._last_mtime = mtime
            return

        if mtime != self._last_mtime:
            self._last_mtime = mtime
            await self._on_change()

    @_watch.before_loop
    async def _before_loop(self):
        try:
            await self.bot.wait_until_ready()
        except Exception:
            pass

    async def _on_change(self):
        log.info("[hotenv] detected change on %s; reloading all cogs...", self.env_path)
        try:
            exts: List[str] = list(self.bot.extensions.keys())
        except Exception:
            log.exception("[hotenv] unable to read bot extensions")
            return
        this_ext = __name__
        try:
            reload_extensions_safely(self.bot, exts, logger=log, skip_self=this_ext)
        except Exception:
            log.exception("[hotenv] scheduling reload failed")
        await asyncio.sleep(0.05)
async def setup(bot: commands.Bot):
    await bot.add_cog(HotEnvReload(bot))