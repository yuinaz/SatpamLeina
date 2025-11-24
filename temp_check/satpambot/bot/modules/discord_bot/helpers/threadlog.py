from satpambot.bot.modules.discord_bot.helpers import static_cfg
async def resolve_log_channel(guild):
    try:
        for ch in guild.text_channels:
            if ch.name==static_cfg.LOG_CHANNEL_NAME:
                return ch
        for ch in guild.channels:
            if getattr(ch,"name",None)==static_cfg.LOG_CHANNEL_NAME:
                return ch
    except Exception:
        pass
    return None
async def maybe_thread(channel):
    try:
        import discord
        if isinstance(channel,(discord.Thread,)):
            return channel
        for th in getattr(channel,"threads",[]):
            if getattr(th,"name","")==static_cfg.LOG_THREAD_NAME:
                return th
        try:
            active=await channel.active_threads()
            for th in active:
                if th.name==static_cfg.LOG_THREAD_NAME:
                    return th
        except Exception:
            pass
        try:
            archived=await channel.archived_threads().flatten()
            for th in archived:
                if th.name==static_cfg.LOG_THREAD_NAME:
                    return th
        except Exception:
            pass
    except Exception:
        pass
    return channel
async def send_text(guild,text:str):
    try:
        ch=await resolve_log_channel(guild)
        if not ch: return
        ch=await maybe_thread(ch)
        await ch.send(text)
    except Exception:
        pass
async def send_embed(guild,embed):
    try:
        ch=await resolve_log_channel(guild)
        if not ch: return
        ch=await maybe_thread(ch)
        await ch.send(embed=embed)
    except Exception:
        pass
async def send_error(guild,text:str):
    await send_text(guild,f"⚠️ {text}")
async def announce_ban(message,reason:str,delete_after:int=15):
    try:
        ch=message.channel
        user=getattr(message.author,"mention",f"<@{message.author.id}>")
        await ch.send(f"🚫 {user} diblokir (alasan: {reason}).",delete_after=delete_after)
    except Exception:
        pass
