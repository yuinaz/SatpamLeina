from __future__ import annotations

import logging, os
from satpambot.config.local_cfg import cfg, cfg_int, cfg_bool

log = logging.getLogger(__name__)

SEV_PREFIX_INFO  = cfg("ALERT_PREFIX_INFO",  "[INFO]")
SEV_PREFIX_WARN  = cfg("ALERT_PREFIX_WARN",  "[WARN]")
SEV_PREFIX_ERROR = cfg("ALERT_PREFIX_ERROR", "[ERROR]")
MENTION_ROLE_ID  = int(cfg_int("OWNER_NOTIFY_MENTION_ROLE_ID", 0) or 0)

def _apply_to_redirect():
    try:
        mod = __import__("satpambot.bot.modules.discord_bot.cogs.a03_owner_notify_redirect_thread", fromlist=["*"])
        old_redirect = getattr(mod, "_redirect_to_thread", None)
        if not callable(old_redirect):
            return
        async def wrapped(*, content=None, embed=None, embeds=None, files=None, **kwargs):
            prefix = cfg("OWNER_NOTIFY_PREFIX","")
            text = str(content or "")
            if "error" in text.lower():
                prefix = SEV_PREFIX_ERROR
            elif "warn" in text.lower() or "warning" in text.lower():
                prefix = SEV_PREFIX_WARN
            else:
                prefix = SEV_PREFIX_INFO if not prefix else prefix
            if prefix and content:
                content = f"{prefix} {content}"
            if MENTION_ROLE_ID:
                content = (content or "") + f" <@&{MENTION_ROLE_ID}>"
            return await old_redirect(content=content, embed=embed, embeds=embeds, files=files, **kwargs)
        setattr(mod, "_redirect_to_thread", wrapped)
        log.info("[alert_prefix_severity] overlay applied (role=%s)", MENTION_ROLE_ID or "none")
    except Exception as e:
        log.warning("[alert_prefix_severity] failed: %s", e)

_apply_to_redirect()