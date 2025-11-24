from .ban_embed import build_ban_embed
import os
import discord
from datetime import datetime, timezone
from modules.database import add_ban_entry, get_recent_bans, get_banlist_message_id, set_banlist_message_id

def _tsfmt(iso):
    try:
        dt = datetime.fromisoformat(iso.replace('Z','+00:00'))
    except Exception:
        dt = datetime.now(timezone.utc)
    return f"<t:{int(dt.timestamp())}:R>"

async def send_ban_embed(guild: discord.Guild, user: discord.Member, reason: str = "", evidence: dict = None):
    evidence = evidence or {}
    ch_id = int(os.getenv("BAN_LOG_CHANNEL_ID") or os.getenv("MOD_COMMAND_CHANNEL_ID") or 0)
    if not ch_id:
        return
    channel = guild.get_channel(ch_id) or (await guild.fetch_channel(ch_id))
    emb = discord.Embed(title="🚫 User Banned", color=discord.Color.red())
    emb.add_field(name="User", value=f"{user.mention} (`{user.id}`)", inline=False)
    emb.add_field(name="Guild", value=f"{guild.name} (`{guild.id}`)", inline=False)
    if reason:
        emb.add_field(name="Reason", value=reason[:1024], inline=False)
    if evidence:
        ev_text = "\n".join([f"**{k}:** {v}" for k,v in evidence.items()])[:1024]
        emb.add_field(name="Evidence", value=ev_text, inline=False)
    emb.set_footer(text="SatpamBot • Auto moderation")
    try:
        await channel.send(embed=emb)
        try:
                await channel.send(stickers=[stk])
        except Exception:
            pass
    except Exception:
        pass

async def upsert_banlist_embed(bot: discord.Client, guild: discord.Guild):
    ch_id = int(os.getenv("MOD_COMMAND_CHANNEL_ID") or 0)
    if not ch_id:
        return
    channel = guild.get_channel(ch_id) or (await guild.fetch_channel(ch_id))
    recent = get_recent_bans(limit=20)
    lines = []
    for r in recent:
        lines.append(f"• `<@{r['user_id']}>` (`{r['user_id']}`) — {_tsfmt(r['ts'])}\n  _{(r['reason'] or 'No reason')[:160]}_")
    desc = "\n".join(lines) if lines else "— belum ada ban —"
    emb = discord.Embed(title="📝 Ban List (Terbaru)", description=desc[:4096], color=discord.Color.orange())
    emb.set_footer(text=f"Total terakhir: {len(recent)} entries")

    msg_id = get_banlist_message_id(str(ch_id))
    message = None
    if msg_id:
        try:
            message = await channel.fetch_message(int(msg_id))
        except Exception:
            message = None
    if message:
        try:
            await message.edit(embed=emb)
        except Exception:
            try:
                new_msg = await channel.send(embed=emb)
                set_banlist_message_id(str(ch_id), str(new_msg.id))
            except Exception:
                pass
    else:
        try:
            new_msg = await channel.send(embed=emb)
            set_banlist_message_id(str(ch_id), str(new_msg.id))
        except Exception:
            pass

async def record_ban_and_log(bot: discord.Client, guild: discord.Guild, user: discord.Member, reason: str = "", evidence: dict = None):
    add_ban_entry(str(user.id), str(guild.id) if guild else "-", reason or "")
    await send_ban_embed(guild, user, reason, evidence or {})
    await upsert_banlist_embed(bot, guild)
