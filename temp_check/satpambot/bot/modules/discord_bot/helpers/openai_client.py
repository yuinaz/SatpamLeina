from __future__ import annotations

# deprecated legacy client shim

def chat_once(*a, **k):
    raise RuntimeError("Legacy client deprecated. Use satpambot.ai.groq_client via call_ai().")

def chat_stream(*a, **k):
    raise RuntimeError("Legacy client deprecated. Use satpambot.ai.groq_client via call_ai().")
