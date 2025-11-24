# -*- coding: utf-8 -*-
"""delete_safe_shim v3
- Idempotent delete (swallow NotFound/Forbidden/10008).
- Protect messages in thread "neuro-lite progress" and keeper-like messages
  from accidental deletion by other cogs.
- **NEW**: allowlist API `allow_delete_for(message_id: int)` so trusted cog
  (e.g., neuro_memory_pinner) can cleanup duplicates safely.
"""
from discord.ext import commands
import logging
import discord

from satpambot.bot.modules.discord_bot.helpers.thread_utils import DEFAULT_THREAD_NAME

log = logging.getLogger(__name__)

_ALLOWED_DELETE_IDS = set()

def allow_delete_for(message_id: int):
    """Permit a single deletion for the given message id."""
    try:
        _ALLOWED_DELETE_IDS.add(int(message_id))
    except Exception:
        pass

def _in_neuro_thread(msg: discord.Message) -> bool:
    try:
        ch = getattr(msg, "channel", None)
        name = (getattr(ch, "name", "") or "").strip().lower()
        return name == (DEFAULT_THREAD_NAME or "").strip().lower()
    except Exception:
        return False

def _is_keeper(msg: discord.Message) -> bool:
    try:
        c = (getattr(msg, "content", "") or "")
        if not isinstance(c, str):
            return False
        c_low = c.lower()
        return ("neuro-lite memory" in c_low) or ("neuro-lite gate status" in c_low) or ("[neuro-lite:" in c_low)
    except Exception:
        return False

def _install_safe_delete_wrapper():
    original_delete = discord.Message.delete
    async def _safe_delete(self: discord.Message, *args, **kwargs):
        mid = int(getattr(self, "id", 0) or 0)
        if mid in _ALLOWED_DELETE_IDS:
            _ALLOWED_DELETE_IDS.discard(mid)
            return await original_delete(self, *args, **kwargs)
        try:
            # PROTECT: neuro thread & keeper messages
            if _in_neuro_thread(self) or _is_keeper(self):
                log.debug("[delete_safe_shim] ignore delete for protected message in #%s", getattr(getattr(self, "channel", None), "name", "?"))
                return None
            return await original_delete(self, *args, **kwargs)
        except discord.NotFound:
            log.debug("[delete_safe_shim] ignore NotFound (msg_id=%s)", getattr(self, "id", "?"))
            return None
        except discord.Forbidden:
            log.debug("[delete_safe_shim] ignore Forbidden (msg_id=%s)", getattr(self, "id", "?"))
            return None
        except discord.HTTPException as e:
            if getattr(e, "code", None) == 10008:
                log.debug("[delete_safe_shim] ignore HTTP 10008 Unknown Message (msg_id=%s)", getattr(self, "id", "?"))
                return None
            raise
    # Always wrap to ensure latest behavior
    discord.Message.delete = _safe_delete
    log.info("[delete_safe_shim] Message.delete patched (v3, neuro protect + allowlist).")

class DeleteSafeShim(commands.Cog):
    def __init__(self, bot: commands.Bot):
        _install_safe_delete_wrapper()
async def setup(bot: commands.Bot):
    await bot.add_cog(DeleteSafeShim(bot))