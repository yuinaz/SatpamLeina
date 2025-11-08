# -*- coding: utf-8 -*-
from __future__ import annotations
import os, logging, re
try:
    import discord
    from discord.ext import commands
except Exception as _e:
    discord=None
    class commands:
        Cog=object
        @staticmethod
        def listener():
            def deco(fn): return fn
            return deco
    _IMPORT_ERR=_e
else:
    _IMPORT_ERR=None
log=logging.getLogger(__name__)
_RX_TITLE=re.compile(r'^\s*Answer\s+by\s+(.+?)\s*$', re.I)
_RX_FOOT=re.compile(r'\bprovider\s*[:=]\s*(gemini|groq)\b', re.I)
def _order():
    raw=os.getenv('QNA_PROVIDER_ORDER','') or os.getenv('LEINA_AI_PROVIDER_ORDER','') or os.getenv('LLM_PROVIDER_ORDER','')
    return [p.strip().lower() for p in raw.replace('|',',').split(',') if p.strip()] or ['gemini','groq']
def _norm(s:str)->str:
    t=(s or '').strip().lower()
    if not t or (t.startswith('{') and t.endswith('}')): return ''
    if 'groq' in t: return 'groq'
    if 'gem' in t: return 'gemini'
    return ''
def _prov(e):
    prov=''
    try:
        m=_RX_TITLE.search(getattr(e,'title','') or ''); 
        if m: prov=_norm(m.group(1))
    except Exception: pass
    if prov: return prov
    try:
        ft=getattr(getattr(e,'footer',None),'text','') or ''
        m=_RX_FOOT.search(ft)
        if m: prov=_norm(m.group(1))
    except Exception: pass
    return prov
def _mode(p):
    if p not in ('gemini','groq'): return None
    order=_order()
    return 'primary' if (order and p==order[0]) else 'fallback'
def _mk(p,m): return f'markers: [QNA][PROVIDER:{p}][MODE:{m}]'
class QnaDualModeMarkersOverlay(commands.Cog if commands!=object else object):
    def __init__(self, bot=None): self.bot=bot
    @getattr(commands,'Cog',object).listener()
    async def on_message(self, message):
        try:
            if not message or not getattr(message,'author',None): return
            if not self.bot or message.author.id != getattr(self.bot.user,'id',None): return
            embeds = getattr(message,'embeds',None) or []
            if not embeds: return
            e=embeds[0]; p=_prov(e); m=_mode(p)
            if not p or not m: return
            try:
                ft=getattr(getattr(e,'footer',None),'text','') or ''
                if 'markers: [QNA]' in ft: return
            except Exception: ft=''
            try:
                e2 = e.copy() if hasattr(e,'copy') else discord.Embed.from_dict(e.to_dict())
                footer = (ft.strip()+('  •  ' if ft.strip() else '')+_mk(p,m))
                e2.set_footer(text=footer)
                await message.edit(embed=e2)
                log.info('[qna-markers] appended for %s/%s', p, m)
            except Exception as ex:
                log.warning('[qna-markers] edit failed: %r', ex)
        except Exception:
            log.exception('[qna-markers] on_message error')
def setup(bot):
    if _IMPORT_ERR is not None: raise _IMPORT_ERR
    try: bot.add_cog(QnaDualModeMarkersOverlay(bot))
    except Exception as e: log.exception('Failed (sync): %s', e)
async def setup(bot):
    if _IMPORT_ERR is not None: raise _IMPORT_ERR
    try: await bot.add_cog(QnaDualModeMarkersOverlay(bot))
    except Exception as e: log.exception('Failed (async): %s', e)
