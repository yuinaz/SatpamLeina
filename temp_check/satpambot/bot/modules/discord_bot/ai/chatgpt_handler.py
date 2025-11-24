from __future__ import annotations

# satpambot/bot/modules/discord_bot/ai/chatgpt_handler.py
from typing import Optional, List, Dict
from satpambot.ai.groq_client import make_groq_client, GroqLLM

_DEFAULT_MODEL = None  # use Groq default from client

def _cli() -> GroqLLM:
    return GroqLLM(make_groq_client())

async def call_ai(prompt: str, model: Optional[str] = _DEFAULT_MODEL, temperature: float = 0.7) -> str:
    cli = _cli()
    messages: List[Dict[str, str]] = [{"role": "user", "content": prompt}]
    return cli.complete(messages)

# backward-compat: keep name but route to Groq
async def call_chatgpt(prompt: str, model: Optional[str] = None, temperature: float = 0.7) -> str:
    return await call_ai(prompt, model=model, temperature=temperature)
