from __future__ import annotations
import logging, inspect, asyncio
from typing import Any
try:
    from discord.ext import commands
except Exception:
    commands = None  # type: ignore

log = logging.getLogger(__name__)

def _patch_add_command(bot: Any):
    orig_add = getattr(bot, "add_command", None)
    orig_remove = getattr(bot, "remove_command", None)
    if not orig_add or getattr(bot, "_add_command_override_patched", False):
        return
    def add_command_guard(cmd, *args, **kwargs):
        try:
            name = getattr(cmd, "name", None) or getattr(cmd, "qualified_name", None)
            if name:
                try:
                    # remove existing conflicting command before adding the new one
                    if callable(orig_remove):
                        removed = orig_remove(name)
                        if removed:
                            log.info("[cmd-override] removed existing command: %s", name)
                except Exception as e:
                    log.info("[cmd-override] remove failed for %s: %r", name, e)
        except Exception:
            pass
        r = orig_add(cmd, *args, **kwargs)
        return r
    bot.add_command = add_command_guard  # type: ignore
    bot._add_command_override_patched = True
    log.info("[cmd-override] bot.add_command patched (last one wins)")

def _patch_add_cog_override(bot: Any):
    # Ensure cog injection uses override=True when available (discord.py >=2.0)
    orig = getattr(bot, "add_cog", None)
    if not orig or getattr(bot, "_add_cog_override_patched", False):
        return
    async def _ensure(cog, *args, **kwargs):
        try:
            # prefer override=True if supported to allow command replacement
            kwargs.setdefault("override", True)
        except Exception:
            pass
        r = orig(cog, *args, **kwargs)
        if inspect.isawaitable(r):
            return await r
        return r
    def wrapper(cog, *args, **kwargs):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        task = loop.create_task(_ensure(cog, *args, **kwargs))
        class _Awaitable:
            def __await__(self):
                return task.__await__()
        return _Awaitable()
    bot.add_cog = wrapper  # type: ignore
    bot._add_cog_override_patched = True
    log.info("[cmd-override] bot.add_cog patched (override=True)")

class CommandOverrideGuard(commands.Cog):
    def __init__(self, bot):
        _patch_add_command(bot)
        _patch_add_cog_override(bot)

async def setup(bot):
    try:
        await bot.add_cog(CommandOverrideGuard(bot))
    except Exception as e:
        log.info("[cmd-override] setup swallowed: %r", e)
