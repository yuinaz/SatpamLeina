import os, logging
log=logging.getLogger(__name__)
PIN_CH=int(os.getenv('XP_STAGE_PIN_CHANNEL_ID','1431178130155896882'))
PIN_MSG=int(os.getenv('XP_STAGE_PIN_MESSAGE_ID','1432060859252998268'))
STRICT=os.getenv('XP_STAGE_STRICT_EDIT_ONLY','1')!='0'
async def update_embed(bot, content:str):
    try:
        ch=bot.get_channel(PIN_CH)
        if not ch: 
            log.warning('[xp-recompute] channel not found: %s', PIN_CH); return False
        try: msg=await ch.fetch_message(PIN_MSG)
        except Exception: msg=None
        if not msg and STRICT:
            log.warning('[xp-recompute] pin message missing & STRICT_EDIT_ONLY=1 (ch=%s msg=%s)', PIN_CH, PIN_MSG)
            return False
        if not msg:
            msg = await ch.send(content)
            try: await msg.pin()
            except Exception: pass
        else:
            await msg.edit(content=content)
        return True
    except Exception as e:
        log.warning('[xp-recompute] update failed: %r', e); return False
