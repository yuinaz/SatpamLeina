import os
from typing import Set

def _parse_ids(val: str | None) -> Set[int]:
    out: Set[int] = set()
    if not val:
        return out
    for tok in str(val).replace(",", " ").split():
        try:
            out.add(int(tok))
        except Exception:
            pass
    return out

MOD_USER_IDS = _parse_ids(os.getenv("MODERATOR_USER_IDS"))
MOD_ROLE_IDS = _parse_ids(os.getenv("MODERATOR_ROLE_IDS"))

def preview_channel_id_from_env() -> int:
    for key in ("MOD_COMMAND_CHANNEL_ID", "DRYRUN_PREVIEW_CHANNEL_ID"):
        v = os.getenv(key)
        if v and str(v).isdigit():
            try:
                return int(v)
            except Exception:
                pass
    return 0

async def is_protected_member(member) -> bool:
    """
    True jika member ini harus dilindungi dari auto-ban.
    """
    if member is None:
        return True
    g = getattr(member, "guild", None)
    if not g:
        return True
    if getattr(member, "bot", False):
        return True
    try:
        if member.id == g.owner_id:
            return True
    except Exception:
        pass
    if member.id in MOD_USER_IDS:
        return True
    perms = getattr(member, "guild_permissions", None)
    if perms and any((
        getattr(perms, "administrator", False),
        getattr(perms, "manage_guild", False),
        getattr(perms, "manage_messages", False),
        getattr(perms, "kick_members", False),
        getattr(perms, "ban_members", False),
    )):
        return True
    if MOD_ROLE_IDS:
        try:
            if any(getattr(r, "id", 0) in MOD_ROLE_IDS for r in getattr(member, "roles", [])):
                return True
        except Exception:
            pass
    try:
        me = getattr(g, "me", None)
        if me and getattr(member, "top_role", None) and member.top_role >= me.top_role:
            return True
    except Exception:
        pass
    return False
