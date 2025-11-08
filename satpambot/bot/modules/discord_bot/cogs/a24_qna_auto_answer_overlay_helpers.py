import os
def qna_title(provider:str)->str:
    base=os.getenv('QNA_TITLE_ISOLATION','Answer by Leina')
    p=(provider or '').strip().title() or 'Leina'
    if '{provider}' in base: return base.replace('{provider}', p)
    if base.lower().startswith('answer by leina'): return f'Answer by {p}'
    return base
def footer_markers(provider:str)->str:
    prov=(provider or '').strip().lower() or 'gemini'
    order=(os.getenv('QNA_PROVIDER_ORDER','gemini,groq') or 'gemini,groq').split(',')[0].strip().lower()
    mode='primary' if prov==order else 'fallback'
    return f'provider={prov}  •  markers: [QNA][PROVIDER:{prov}][MODE:{mode}]'
