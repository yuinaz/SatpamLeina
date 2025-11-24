from __future__ import annotations
import logging
from discord.ext import commands
from satpambot.bot.modules.discord_bot.helpers.intish import parse_intish
log = logging.getLogger(__name__)
class XpWriteGuardOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
            _orig_cmd = UpstashClient.cmd
            async def _patched(self, *args):
                try:
                    if not args: return await _orig_cmd(self, *args)
                    if isinstance(args[0], (list, tuple)):
                        op, key, *rest = args[0] + tuple(args[1:])
                    else:
                        op, key, *rest = args
                    if isinstance(op, bytes): op = op.decode("utf-8","ignore")
                    if isinstance(key, bytes): key = key.decode("utf-8","ignore")
                    if str(op).upper()=="SET" and str(key) in {"xp:bot:senior_total","xp:bot:senior_total_v2"} and rest:
                        val = rest[0]
                        ok, v = parse_intish(val)
                        if ok and v is not None:
                            rest = (str(int(v)),) + tuple(rest[1:])
                            log.warning("[xp-guard] coerced write %s -> %s", key, rest[0])
                            return await _orig_cmd(self, op, key, *rest)
                        if isinstance(val, (str, bytes)) and str(val).strip().startswith("{"):
                            log.error("[xp-guard] blocked JSON write to %s: %.80s", key, val)
                            return {"result":"BLOCKED"}
                except Exception as e:
                    log.debug("[xp-guard] patch err: %r", e)
                return await _orig_cmd(self, *args)
            UpstashClient.cmd = _patched
            log.info("[xp-guard] UpstashClient.cmd patched (write guard active)")
        except Exception as e:
            log.debug("[xp-guard] skip patch: %r", e)
async def setup(bot): await bot.add_cog(XpWriteGuardOverlay(bot))
def setup(bot):
    try: bot.add_cog(XpWriteGuardOverlay(bot))
    except Exception: pass