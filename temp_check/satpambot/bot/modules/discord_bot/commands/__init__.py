from .general_commands import register_general_commands
from .moderation_commands import register_moderation_commands
from .image_commands import register_image_commands
from .debug_commands import register_debug_commands

def register_commands(bot):
    register_general_commands(bot)
    register_moderation_commands(bot)
    register_image_commands(bot)
    register_debug_commands(bot)
