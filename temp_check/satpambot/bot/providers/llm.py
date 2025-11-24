# -*- coding: utf-8 -*-
"""
LLM provider (AUTO with fallback) with user defaults:
- GROQ default:    llama-3.1-8b-instant
- GEMINI default:  gemini-2.5-flash-lite
You can still override via env: LLM_GROQ_MODEL / LLM_GEMINI_MODEL
"""
from __future__ import annotations
import os, json, logging
from typing import Any, Dict, List, Optional
import httpx

log = logging.getLogger(__name__)

def _env(name: str, default: Optional[str]=None) -> Optional[str]:
    v = os.environ.get(name)
    return v if (v is not None and v != "") else default

class LLM:
    def __init__(self) -> None:
        self.provider = (_env("LLM_PROVIDER", "auto") or "auto").lower()
        self.groq_key = _env("GROQ_API_KEY")
        self.google_key = _env("GOOGLE_API_KEY")
        # User-specified defaults:
        self.groq_model = _env("LLM_GROQ_MODEL", "llama-3.1-8b-instant")
        self.gemini_model = _env("LLM_GEMINI_MODEL", "gemini-2.5-flash-lite")
        self.timeout = int(_env("LLM_TIMEOUT", "60"))

    async def chat(self,
                   prompt: Optional[str]=None,
                   messages: Optional[List[Dict[str, Any]]]=None,
                   system_prompt: Optional[str]=None,
                   temperature: float=0.2,
                   max_tokens: Optional[int]=None) -> Optional[str]:
        order: List[str] = []
        p = self.provider
        if p == "groq":
            order = ["groq"]
        elif p == "gemini":
            order = ["gemini"]
        else:  # AUTO
            if self.groq_key: order.append("groq")
            if self.google_key: order.append("gemini")
            if not order:
                log.warning("[llm] AUTO: no provider available (GROQ_API_KEY/GOOGLE_API_KEY missing)")
                return None

        last_err: Optional[Exception] = None
        for prov in order:
            try:
                if prov == "groq":
                    log.info("[llm] using GROQ model=%s", self.groq_model)
                    out = await self.chat_groq(prompt, messages, system_prompt, temperature, max_tokens)
                else:
                    log.info("[llm] using GEMINI model=%s", self.gemini_model)
                    out = await self.chat_gemini(prompt, messages, system_prompt, temperature, max_tokens)
                if out: return out
            except Exception as e:
                last_err = e
                log.warning("[llm] %s failed: %r (fallback next if available)", prov, e)
        if last_err:
            log.warning("[llm] all providers failed; last_error=%r", last_err)
        return None

    async def chat_groq(self,
                        prompt: Optional[str],
                        messages: Optional[List[Dict[str, Any]]],
                        system_prompt: Optional[str],
                        temperature: float,
                        max_tokens: Optional[int]) -> Optional[str]:
        if not self.groq_key:
            raise RuntimeError("GROQ_API_KEY missing")
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"}
        msgs: List[Dict[str, str]] = []
        if system_prompt:
            msgs.append({"role": "system", "content": str(system_prompt)})
        for m in (messages or []):
            role = str(m.get("role", "user"))
            content = str(m.get("content", ""))
            if content:
                msgs.append({"role": role, "content": content})
        if (not msgs) and prompt:
            msgs.append({"role": "user", "content": str(prompt)})
        body: Dict[str, Any] = {"model": self.groq_model, "messages": msgs, "temperature": float(temperature), "stream": False}
        if isinstance(max_tokens, int) and max_tokens > 0:
            body["max_tokens"] = max_tokens
        async with httpx.AsyncClient(timeout=self.timeout) as cli:
            r = await cli.post(url, headers=headers, json=body)
            if r.status_code >= 400:
                log.warning("[llm:groq] %s %s", r.status_code, r.text[:500])
                return None
            data = r.json()
            ch = (data.get("choices") or [{}])[0]
            msg = (ch.get("message") or {})
            return (msg.get("content") or "").strip() or None

    async def chat_gemini(self,
                          prompt: Optional[str],
                          messages: Optional[List[Dict[str, Any]]],
                          system_prompt: Optional[str],
                          temperature: float,
                          max_tokens: Optional[int]) -> Optional[str]:
        if not self.google_key:
            raise RuntimeError("GOOGLE_API_KEY missing")
        model = self.gemini_model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.google_key}"
        texts: List[str] = []
        if system_prompt: texts.append(str(system_prompt))
        for m in (messages or []):
            c = str(m.get("content", ""))
            if c: texts.append(c)
        if prompt: texts.append(str(prompt))
        merged = "\n\n".join(texts).strip() or " "
        genconf: Dict[str, Any] = {"temperature": float(temperature)}
        if isinstance(max_tokens, int) and max_tokens > 0:
            genconf["maxOutputTokens"] = max_tokens
        body = {"contents": [{"role":"user","parts":[{"text": merged}]}], "generationConfig": genconf}
        async with httpx.AsyncClient(timeout=self.timeout) as cli:
            r = await cli.post(url, json=body)
            if r.status_code >= 400:
                log.warning("[llm:gemini] %s %s", r.status_code, r.text[:500])
                return None
            data = r.json()
            cands = data.get("candidates") or []
            if not cands: return None
            parts = (cands[0].get("content") or {}).get("parts") or []
            return "".join(p.get("text","") for p in parts) or None
