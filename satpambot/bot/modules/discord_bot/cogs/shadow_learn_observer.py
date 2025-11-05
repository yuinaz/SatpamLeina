from __future__ import annotations
import os, time, logging
import discord
from discord.ext import commands
log = logging.getLogger(__name__)
PER_EXPOSURE_XP = int(os.getenv("SHADOW_EXPOSURE_XP","15") or "15")
USER_COOLDOWN_SEC = int(os.getenv("SHADOW_XP_COOLDOWN_SEC","180") or "180")
def _parse_ids(raw): 
    s=set()
    for p in (raw or "").replace(";",",").split(","):
        p=p.strip()
        if p: 
            try: s.add(int(p))
            except: pass
    return s
SKIP_IDS = _parse_ids(os.getenv("SHADOW_SKIP_IDS",""))
try:
    _qna=int(os.getenv("LEARNING_QNA_CHANNEL_ID", os.getenv("QNA_CHANNEL_ID","0")) or "0")
    if _qna: SKIP_IDS.add(_qna)
except: pass
class ShadowLearnObserver(commands.Cog):
    def __init__(self, bot): self.bot=bot; self._last={}
    def _ok(self, uid):
        now=time.time(); last=self._last.get(uid,0.0)
        if now-last<USER_COOLDOWN_SEC: return False
        self._last[uid]=now; return True
    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        try:
            if m.guild is None or m.author.bot: return
            ch_id = getattr(getattr(m, "channel", None), "id", None)
            if ch_id and ch_id in SKIP_IDS: return
            if PER_EXPOSURE_XP>0 and self._ok(m.author.id):
                for evt in ("xp_add","satpam_xp","xp_award"):
                    try: self.bot.dispatch(evt, m.author.id, PER_EXPOSURE_XP, "shadow_exposure")
                    except: pass
        except Exception:
            log.exception("[shadow_learn_observer] on_message error")
async def setup(bot): await bot.add_cog(ShadowLearnObserver(bot))
