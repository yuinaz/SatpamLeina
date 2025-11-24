from __future__ import annotations

import os
import discord

# Optional: can be set via ENV later
MOD_ROLE_IDS = {
    int(x) for x in os.getenv("MOD_ROLE_IDS", "").replace(" ", "").split(",") if x.isdigit()
}
MOD_ROLE_NAMES = [s.strip().lower() for s in os.getenv(
    "MOD_ROLE_NAMES", "moderator,admin,mod"
).split(",") if s.strip()]

def is_mod_or_admin(m: discord.Member) -> bool:
    if not isinstance(m, discord.Member):
        return False
    gp = m.guild_permissions
    if gp.administrator or gp.ban_members or gp.manage_guild or gp.manage_messages:
        return True
    if MOD_ROLE_IDS and any(r.id in MOD_ROLE_IDS for r in m.roles):
        return True
    names = [r.name.lower() for r in m.roles]
    return any(any(tok in n for tok in MOD_ROLE_NAMES) for n in names)
