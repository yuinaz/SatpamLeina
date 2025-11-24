import os, time, logging
from discord.ext import commands
ENABLE=os.getenv('DISABLE_DUPLICATE_QNA','1')!='0'
WINDOW_SEC=int(os.getenv('QNA_DEDUP_WINDOW_SEC','8'))
log=logging.getLogger(__name__)
class DisableDuplicateQNA(commands.Cog):
    def __init__(self, bot: commands.Bot): 
        self.bot=bot; self._last={}
    @commands.Cog.listener()
    async def on_message(self, message):
        if not ENABLE or not message or message.author.bot: return
        content=(message.content or '').strip()
        if not content: return
        ch=getattr(message,'channel',None); 
        if not ch: return
        now=time.time(); key=ch.id; h=hash(content); prev=self._last.get(key)
        if prev and prev[0]==h and (now-prev[1])<=WINDOW_SEC:
            try: await message.delete(); log.warning('[dup-qna] dropped duplicate in %s', key)
            except Exception as e: log.warning('[dup-qna] delete failed: %s', e)
            return
        self._last[key]=(h,now)
async def setup(bot): 
    if not ENABLE: return
    try: await bot.add_cog(DisableDuplicateQNA(bot))
    except Exception as e: log.error('[dup-qna] setup failed: %s', e)
