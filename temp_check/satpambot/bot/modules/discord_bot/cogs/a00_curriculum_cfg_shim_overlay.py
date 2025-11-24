
from __future__ import annotations
import os, logging
from importlib import import_module
from discord.ext import commands

log = logging.getLogger(__name__)

def _derive_channel_id() -> int | None:
    keys = ["LEINA_CURRICULUM_CHANNEL_ID", "CURRICULUM_REPORT_CHANNEL_ID", "LOG_CHANNEL_ID"]
    for k in keys:
        v = os.getenv(k)
        if v and str(v).isdigit():
            try:
                n = int(v)
                if n > 0:
                    return n
            except Exception:
                pass
    return None

class CurriculumCfgShim(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._apply()

    def _apply(self):
        try:
            a20 = import_module("satpambot.bot.modules.discord_bot.cogs.a20_curriculum_tk_sd")
        except Exception as e:
            log.warning("[curriculum_cfg_shim] cannot import a20_curriculum_tk_sd: %r", e)
            return
        if getattr(a20, "_load_cfg", None) is None:
            def _load_cfg():
                cid = _derive_channel_id()
                return {"report_channel_id": cid}
            try:
                setattr(a20, "_load_cfg", _load_cfg)
                log.info("[curriculum_cfg_shim] injected a20._load_cfg (cid=%s)", _derive_channel_id())
            except Exception as e:
                log.warning("[curriculum_cfg_shim] failed to inject: %r", e)

async def setup(bot):
    await bot.add_cog(CurriculumCfgShim(bot))
