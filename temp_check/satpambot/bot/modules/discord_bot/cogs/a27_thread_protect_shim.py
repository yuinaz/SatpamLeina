# a27_thread_protect_shim.py
import logging, json
from pathlib import Path
log=logging.getLogger(__name__)
def _load_protected_ids():
    ids=set()
    try:
        cfgp=Path("config/protect_threads.json")
        if cfgp.exists():
            data=json.loads(cfgp.read_text(encoding="utf-8"))
            for x in (data.get("protect_threads") or []):
                try: ids.add(int(x))
                except Exception: pass
    except Exception: log.warning("[thread_protect] failed reading protect_threads.json", exc_info=True)
    try:
        from importlib import import_module
        a20=import_module("satpambot.bot.modules.discord_bot.cogs.a20_curriculum_tk_sd")
        c=a20._load_cfg(); cid=int(c.get("report_channel_id") or 0)
        if cid: ids.add(cid)
    except Exception: pass
    return ids
PROTECT_IDS=_load_protected_ids()
if PROTECT_IDS: log.info("[thread_protect] active for ids=%s", ",".join(map(str, sorted(PROTECT_IDS))))
else: log.info("[thread_protect] no ids configured; shim idle")
try:
    from discord.message import Message
    _orig_delete=Message.delete
    async def _guarded_delete(self,*args,**kwargs):
        try:
            ch_id=int(getattr(getattr(self,"channel",None),"id",0) or 0)
            if ch_id in PROTECT_IDS:
                log.info("[thread_protect] skip Message.delete id=%s in protected thread=%s", getattr(self,"id","?"), ch_id); return
        except Exception: log.warning("[thread_protect] guard delete check failed", exc_info=True)
        return await _orig_delete(self,*args,**kwargs)
    Message.delete=_guarded_delete; log.info("[thread_protect] Message.delete patched")
except Exception: log.warning("[thread_protect] failed to patch Message.delete", exc_info=True)
try:
    from discord.channel import TextChannel, Thread
    _orig_tc_purge=getattr(TextChannel,"purge",None)
    if _orig_tc_purge:
        async def _guarded_tc_purge(self,*args,**kwargs):
            ch_id=int(getattr(self,"id",0) or 0)
            if ch_id in PROTECT_IDS:
                log.info("[thread_protect] skip TextChannel.purge on protected id=%s", ch_id); return []
            return await _orig_tc_purge(self,*args,**kwargs)
        TextChannel.purge=_guarded_tc_purge; log.info("[thread_protect] TextChannel.purge patched")
    _orig_th_purge=getattr(Thread,"purge",None)
    if _orig_th_purge:
        async def _guarded_th_purge(self,*args,**kwargs):
            ch_id=int(getattr(self,"id",0) or 0)
            if ch_id in PROTECT_IDS:
                log.info("[thread_protect] skip Thread.purge on protected id=%s", ch_id); return []
            return await _orig_th_purge(self,*args,**kwargs)
        Thread.purge=_guarded_th_purge; log.info("[thread_protect] Thread.purge patched")
except Exception: log.warning("[thread_protect] failed to patch purge", exc_info=True)
async def setup(bot): return
