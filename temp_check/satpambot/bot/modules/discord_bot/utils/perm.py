import os
from discord.ext import commands
import discord

def _ids(s: str):
    out=set()
    for p in (s or '').replace(';',',').split(','):
        p=p.strip()
        if not p: continue
        try: out.add(int(p))
        except: pass
    return out

DEFAULT_NAMES = "admin, administrator, moderator, mod, staff"
NAMES = {p.strip().lower() for p in (os.getenv("MOD_ROLE_NAMES", DEFAULT_NAMES).replace(';',',')).split(',') if p.strip()}
RID   = _ids(os.getenv("MOD_ROLE_IDS",""))
UID   = _ids(os.getenv("MOD_USER_IDS",""))

def is_mod(member: discord.Member)->bool:
    if member is None: return False
    if member.id in UID: return True
    # roles by id
    ids={int(r.id) for r in getattr(member,'roles',[]) if r}
    if ids & RID: return True
    # roles by name
    names={str(getattr(r,'name','')).strip().lower() for r in getattr(member,'roles',[]) if r}
    if names & NAMES: return True
    # fallback to permissions
    perms = getattr(member, 'guild_permissions', None)
    if perms and (perms.administrator or perms.ban_members or perms.kick_members or perms.manage_messages):
        return True
    return False

def require_mod():
    async def pred(ctx: commands.Context)->bool:
        if not ctx.guild: raise commands.CheckFailure("Gunakan perintah ini di dalam server.")
        m = ctx.author if isinstance(ctx.author, discord.Member) else ctx.guild.get_member(ctx.author.id)
        if not m: raise commands.CheckFailure("Tidak bisa mengambil data member.")
        if not is_mod(m): raise commands.CheckFailure("Kamu tidak punya izin untuk menjalankan perintah ini.")
        me = ctx.guild.me
        if not (me and (me.guild_permissions.ban_members or me.guild_permissions.administrator)):
            raise commands.CheckFailure("Bot tidak memiliki izin ban di server ini.")
        return True
    return commands.check(pred)
