
"""
Groq client shim for smoke tests.
Avoids real network calls, provides a stable async interface.
"""
from typing import Any, Dict, List, Optional
import asyncio

# Public API used by cogs
async def groq_chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    stream: bool = False,
    max_tokens: Optional[int] = None,
    temperature: float = 0.2,
    timeout: Optional[float] = None,
) -> str:
    # In smoke mode, just return a deterministic string.
    await asyncio.sleep(0)  # let event loop tick
    # Extract last user content if available to keep tests predictable
    try:
        last = next((m["content"] for m in reversed(messages) if m.get("role") in {"user", "system"}), "")
    except Exception:
        last = ""
    prefix = "[groq:stub] "
    return prefix + (last[:200] if isinstance(last, str) else "")

# Optional sync helper used in some places; safe fallback
def groq_chat_sync(messages: List[Dict[str, str]], **kwargs) -> str:
    try:
        return asyncio.get_event_loop().run_until_complete(groq_chat(messages, **kwargs))
    except RuntimeError:
        # In case there's no running loop, create a new one
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(groq_chat(messages, **kwargs))
        finally:
            loop.close()
