# satpambot/bot/modules/discord_bot/helpers/prefix_guard.py
from typing import Iterable
from discord import Member
from discord.ext import commands

# Role moderator default (boleh kamu ubah nanti, tidak wajib)
DEFAULT_MOD_ROLES: set[str] = {"Admin", "Administrator", "Moderator", "Mod", "Staff"}

def is_mod(user: Member, allowed_roles: Iterable[str] | None = None) -> bool:
    # Aman untuk DM/Thread: kalau bukan Member (user di DM), bukan mod
    if not isinstance(user, Member):
        return False
    roles = set(allowed_roles or DEFAULT_MOD_ROLES)
    # Owner guild = mod
    if user.guild and user.guild.owner_id == user.id:
        return True
    # Permission admin/manage cukup dianggap mod
    perms = getattr(user, "guild_permissions", None)
    if perms and (getattr(perms, "administrator", False) or getattr(perms, "manage_guild", False) or getattr(perms, "manage_messages", False)):
        return True
    # Cek role name (tahan terhadap exception)
    try:
        if any((r.name in roles) for r in getattr(user, "roles", [])):
            return True
    except Exception:
        pass
    return False

async def get_prefix(bot: commands.Bot, message):
    # Aman untuk event tanpa message/author
    if message is None or getattr(message, "author", None) is None:
        return commands.when_mentioned(bot, message)
    author = message.author
    # Abaikan bot lain
    if getattr(author, "bot", False):
        return commands.when_mentioned(bot, message)
    # Hanya MOD bisa pakai '!' + mention
    if is_mod(author):
        return commands.when_mentioned_or("!")(bot, message)
    # Non-mod: hanya mention sebagai prefix (silent, tanpa error)
    return commands.when_mentioned(bot, message)
