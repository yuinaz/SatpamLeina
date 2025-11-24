import os
TRUE={'1','true','yes','on','y','t'}
def _flag(n,d=False): v=os.getenv(n); return d if v is None else (str(v).strip().lower() in TRUE)
def _str(n,d=''): v=os.getenv(n); return str(v) if v is not None else d
def _first_nonempty(*vals):
    for v in vals:
        if v and str(v).strip(): return str(v).strip()
    return ''
def _split_order(v): return [p.strip().lower() for p in v.replace('|',',').split(',') if p.strip()] if v else []
def select_qna_provider():
    forced=_str('QNA_FORCE_PROVIDER','').strip().lower()
    strict=_flag('QNA_STRICT_FORCE',False)
    dis_gem=_flag('GEMINI_FORCE_DISABLE',False)
    dis_grq=_flag('GROQ_FORCE_DISABLE',False)
    if forced in ('groq','gemini'):
        if forced=='groq' and not dis_grq: return 'groq','forced'
        if forced=='gemini' and not dis_gem: return 'gemini','forced'
    order=_first_nonempty(_str('QNA_PROVIDER_ORDER',''),_str('QNA_PROVIDER_PRIORITY',''),_str('QNA_PROVIDER',''),_str('LEINA_AI_PROVIDER_ORDER',''),_str('LLM_PROVIDER_ORDER',''),_str('LLM_PROVIDER','')) or 'gemini,groq'
    for p in _split_order(order):
        if p=='groq' and not dis_grq: return 'groq','order'
        if p=='gemini' and not dis_gem: return 'gemini','order'
    if not dis_grq: return 'groq','default'
    if not dis_gem: return 'gemini','default'
    return 'gemini','emergency'
