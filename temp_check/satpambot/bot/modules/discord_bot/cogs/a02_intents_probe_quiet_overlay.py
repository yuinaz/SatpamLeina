from __future__ import annotations

import logging
log = logging.getLogger(__name__)
try:
    import satpambot.bot.modules.discord_bot.cogs.intents_probe as ip
    setattr(ip, "SUPPRESS_WARN", True)
    logging.getLogger("satpambot.bot.modules.discord_bot.cogs.intents_probe").setLevel(logging.ERROR)
    log.info("[intents_probe_quiet] applied")
except Exception as e:
    log.debug("[intents_probe_quiet] not applied: %s", e)
async def setup(_bot):
    return