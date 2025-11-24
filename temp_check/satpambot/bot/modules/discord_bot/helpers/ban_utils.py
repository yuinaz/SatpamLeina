from __future__ import annotations

import logging
import discord
log = logging.getLogger(__name__)

async def safe_ban_7d(guild: discord.Guild, user: discord.abc.Snowflake, reason: str = "SatpamBot: policy violation") -> bool:
    try:
        await guild.ban(user, reason=reason, delete_message_days=7)  # type: ignore
        return True
    except TypeError:
        try:
            await guild.ban(user, reason=reason, delete_message_seconds=7*24*3600)  # type: ignore
            return True
        except Exception as e:
            log.warning("safe_ban_7d fallback failed: %r", e)
            return False
    except discord.Forbidden:
        log.error("safe_ban_7d: missing permissions for user %s", getattr(user, "id", "?"))
        return False
    except Exception as e:
        log.error("safe_ban_7d failed: %r", e)
        return False
