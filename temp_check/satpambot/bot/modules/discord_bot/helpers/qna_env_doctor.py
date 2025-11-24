\
from __future__ import annotations
import os, json, logging, pathlib
from typing import Dict, Tuple
from satpambot.config.auto_defaults import cfg_str, cfg_int
log=logging.getLogger(__name__)
def _exists(p:str)->bool:
    try: return pathlib.Path(p).exists()
    except Exception: return False
def collect()->Dict[str,str]:
    d={}
    d["QNA_CHANNEL_ID"]=str(cfg_int("QNA_CHANNEL_ID",0) or 0)
    d["QNA_PROVIDER_ORDER"]=cfg_str("QNA_PROVIDER","groq")
    d["QNA_TOPICS_PATH"]=cfg_str("QNA_TOPICS_PATH","data/config/qna_topics.json")
    d["GROQ_API_KEY"]=os.getenv("GROQ_API_KEY","")
    d["GROQ_MODEL"]=cfg_str("GROQ_MODEL",os.getenv("LLM_GROQ_MODEL","llama-3.1-8b-instant"))
    d["GROQ_BASE_URL"]=os.getenv("GROQ_BASE_URL","https://api.groq.com/openai/v1")
    d["GEMINI_API_KEY"]=os.getenv("GEMINI_API_KEY","") or os.getenv("GOOGLE_API_KEY","")
    d["GEMINI_MODEL"]=cfg_str("GEMINI_MODEL",os.getenv("LLM_GEMINI_MODEL","gemini-2.5-flash"))
    d["GEMINI_BASE_URL"]=os.getenv("GEMINI_BASE_URL","https://generativelanguage.googleapis.com")
    return d
def validate()->Tuple[bool,str]:
    env=collect(); issues=[]
    tp=env["QNA_TOPICS_PATH"]
    if not _exists(tp): issues.append(f"QNA_TOPICS_PATH missing: {tp}")
    else:
        try:
            data=json.load(open(tp,"r",encoding="utf-8"))
            cnt=len(data) if isinstance(data,list) else sum(len(v) for v in data.values() if isinstance(v,list))
            if cnt<=0: issues.append(f"Topics file is empty: {tp}")
        except Exception as e:
            issues.append(f"Topics unreadable: {tp} ({e!r})")
    if not env["QNA_CHANNEL_ID"].isdigit() or int(env["QNA_CHANNEL_ID"])<=0:
        issues.append(f"QNA_CHANNEL_ID invalid: {env['QNA_CHANNEL_ID']}")
    order=[p.strip().lower() for p in env["QNA_PROVIDER_ORDER"].split(",") if p.strip()]
    if not order: order=["groq"]
    for p in order:
        if p=="groq" and not env["GROQ_API_KEY"]: issues.append("GROQ_API_KEY missing but provider order includes 'groq'")
        if p=="gemini" and not env["GEMINI_API_KEY"]: issues.append("GEMINI_API_KEY/GOOGLE_API_KEY missing but provider order includes 'gemini'")
    ok=len(issues)==0; summary="OK" if ok else "; ".join(issues)
    if not ok: log.warning("[envdoctor] %s",summary)
    else: log.info("[envdoctor] OK (order=%s, channel=%s, topics=%s)",order,env["QNA_CHANNEL_ID"],tp)
    return ok, summary
