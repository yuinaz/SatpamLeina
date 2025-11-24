
# a00_cog_and_command_dedupe_guard_overlay.py
# Patches discord.ext.commands.Bot to:
#  - replace existing commands with the same name ("last one wins")
#  - replace existing cogs with the same qualified_name
# Prevents CommandRegistrationError on hot reloads/multi-autoloaders.

import logging
from discord.ext import commands

_CMD_PATCH_FLAG = "_patched_by_cmd_dedupe_guard"
_COG_PATCH_FLAG = "_patched_by_cog_dedupe_guard"

def _patch_add_command():
    Bot = commands.Bot
    if getattr(Bot.add_command, _CMD_PATCH_FLAG, False):
        return

    original_add_command = Bot.add_command

    def safe_add_command(self, command):
        try:
            name = command.name
            existing = self.get_command(name)
            if existing is not None:
                winner_mod = getattr(command.callback, "__module__", "?")
                loser_mod  = getattr(existing.callback, "__module__", "?")
                winner_cog = type(command.cog).__name__ if command.cog else "<no-cog>"
                loser_cog  = type(existing.cog).__name__ if existing.cog else "<no-cog>"
                logging.warning(
                    "[cmd-guard] overriding command '%s': %s.%s -> %s.%s",
                    name, loser_mod, loser_cog, winner_mod, winner_cog
                )
                try:
                    self.remove_command(name)
                except Exception as e:
                    logging.exception("[cmd-guard] remove_command('%s') failed: %r", name, e)
        except Exception as e:
            logging.exception("[cmd-guard] pre-add check failed: %r", e)
        return original_add_command(self, command)

    safe_add_command.__dict__[_CMD_PATCH_FLAG] = True
    Bot.add_command = safe_add_command
    logging.warning("[cmd-guard] bot.add_command patched (last one wins)")

def _patch_add_cog():
    Bot = commands.Bot
    if getattr(Bot.add_cog, _COG_PATCH_FLAG, False):
        return

    original_add_cog = Bot.add_cog

    def safe_add_cog(self, cog, *args, **kwargs):
        try:
            qn = getattr(cog, "qualified_name", None) or type(cog).__name__
            existing = self.get_cog(qn)
            if existing is not None:
                logging.warning("[cog-guard] overriding cog '%s': %s -> %s", qn, type(existing).__name__, type(cog).__name__)
                try:
                    self.remove_cog(qn)
                except Exception as e:
                    logging.exception("[cog-guard] remove_cog('%s') failed: %r", qn, e)
        except Exception as e:
            logging.exception("[cog-guard] pre-add check failed: %r", e)
        return original_add_cog(self, cog, *args, **kwargs)

    safe_add_cog.__dict__[_COG_PATCH_FLAG] = True
    Bot.add_cog = safe_add_cog
    logging.warning("[cog-guard] bot.add_cog patched (dedupe by qualified_name)")

def setup_patch():
    _patch_add_command()
    _patch_add_cog()

# Apply patches at import time.
setup_patch()

async def setup(bot):
    logging.debug("[cog/cmd-guard] overlay setup complete")
