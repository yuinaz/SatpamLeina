from __future__ import annotations

import logging
from satpambot.config.local_cfg import cfg_int
log = logging.getLogger(__name__)
QNA_ID = int(cfg_int("LEARNING_QNA_CHANNEL_ID", 0) or 0)
def _apply(mod_name, attr):
    try:
        mod = __import__(mod_name, fromlist=["*"])
        setattr(mod, attr, QNA_ID)
        log.info("[qna_channel_overlay] %s.%s = %s", mod_name, attr, QNA_ID)
    except Exception as e:
        log.debug("[qna_channel_overlay] %s: %s", mod_name, e)
try:
    if QNA_ID:
        _apply("satpambot.bot.modules.discord_bot.cogs.selfheal_learning_bridge", "QNA_CHANNEL_ID")
        _apply("satpambot.bot.modules.discord_bot.cogs.neuro_shadow_bridge", "QNA_CHANNEL_ID")
        _apply("satpambot.bot.modules.discord_bot.cogs.learning_passive_observer", "QNA_CHANNEL_ID")
        _apply("satpambot.bot.modules.discord_bot.cogs.qna_dual_provider", "QNA_CHANNEL_ID")
except Exception as e:
    log.warning("[qna_channel_overlay] failed: %s", e)