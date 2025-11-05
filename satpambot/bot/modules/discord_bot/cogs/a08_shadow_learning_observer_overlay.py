from __future__ import annotations
import os, time, logging
import discord
from discord.ext import commands
log = logging.getLogger(__name__)
def _env_bool(k, d=False):
    v=os.getenv(k); 
    if v is None or v=='': return d
    return str(v).lower() in ('1','true','yes','on')
def _ids(raw):
    s=set()
    for p in (raw or '').replace(';',',').split(','):
        p=p.strip()
        if not p: continue
        try: s.add(int(p))
        except: pass
    return s
XP = int(os.getenv('SHADOW_EXPOSURE_XP','15') or '15')
COOLDOWN = int(os.getenv('SHADOW_XP_COOLDOWN_SEC','180') or '180')
ENABLE = _env_bool('SHADOW_ENABLE', True)
SKIP = _ids(os.getenv('SHADOW_SKIP_IDS','')) | _ids(os.getenv('LEARNING_SKIP_CHANNEL_IDS',''))
try:
    qna = int(os.getenv('LEARNING_QNA_CHANNEL_ID', os.getenv('QNA_CHANNEL_ID','0')) or '0')
    if qna: SKIP.add(qna)
except: pass
class ShadowLearningObserverOverlay(commands.Cog):
    def __init__(self, bot): self.bot=bot; self._last={}
    def _ok(self, uid):
        import time
        now=time.time(); last=self._last.get(uid,0.0)
        if now-last<COOLDOWN: return False
        self._last[uid]=now; return True
    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if not ENABLE or m.guild is None or m.author.bot: return
        ch = getattr(m, 'channel', None); ch_id = getattr(ch, 'id', None)
        if ch_id and ch_id in SKIP: return
        if XP>0 and self._ok(m.author.id):
            for evt in ('satpam_xp','xp_add','xp_award'):
                try: self.bot.dispatch(evt, m.author.id, XP, 'shadow_exposure')
                except: pass
            log.debug('[shadow-observer] +%s XP -> user=%s ch=%s', XP, m.author.id, ch_id)
async def setup(bot): await bot.add_cog(ShadowLearningObserverOverlay(bot))
