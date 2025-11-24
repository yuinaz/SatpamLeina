import os, logging, importlib
log=logging.getLogger(__name__)
_TRUE={'1','true','yes','on','y','t'}
def _flag(n,d=False): v=os.getenv(n); return d if v is None else (str(v).strip().lower() in _TRUE)
def _set(k,v): os.environ[k]=str(v)
def _disable_mod(mname):
    try: m=importlib.import_module(mname)
    except Exception: return False
    changed=False
    for attr in ('ENABLE','ENABLED','ACTIVE','Active'):
        if hasattr(m, attr):
            try: setattr(m, attr, False); changed=True
            except Exception: pass
    return changed
def _apply():
    forced=(os.getenv('QNA_FORCE_PROVIDER','') or '').strip().lower()
    if not forced: return
    strict=_flag('QNA_STRICT_FORCE', True)
    if strict:
        for k in ('QNA_ALLOW_FALLBACK','QNA_ALLOW_FALLBACK_WHEN_FORCED','QNA_AUTOFALLBACK','QNA_AUTOFAILOVER','QNA_AUTOPILOT'):
            _set(k,'0')
        if forced=='groq': _set('GEMINI_FORCE_DISABLE','1')
        elif forced=='gemini': _set('GROQ_FORCE_DISABLE','1')
        for mod in (
            'satpambot.bot.modules.discord_bot.cogs.a00_qna_provider_autofailover_local_overlay',
            'satpambot.bot.modules.discord_bot.cogs.a00_qna_provider_autofailover_quota_overlay',
            'satpambot.bot.modules.discord_bot.cogs.a24_qna_autopilot_scheduler',
        ): _disable_mod(mod)
    log.warning('[qna-force-lock] forced=%s strict=%s', forced or '-', strict)
try: _apply()
except Exception: log.exception('[qna-force-lock] init failed')
async def setup(bot):
    try: _apply()
    except Exception: log.exception('[qna-force-lock] setup failed')
