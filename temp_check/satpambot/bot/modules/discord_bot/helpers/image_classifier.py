from __future__ import annotations

# satpambot/bot/modules/discord_bot/helpers/image_classifier.py
from typing import Optional, List, Dict, Any
import logging

log = logging.getLogger(__name__)

def classify(buffer: bytes, *, hint: str = "") -> Dict[str, Any]:
    """Safe placeholder classifier.
    This keeps runtime stable without relying on any external vendor literal.
    Replace with satpambot.ai.groq_client vision if available in your environment.
    """
    # Lightweight heuristic fallback:
    size = len(buffer) if buffer is not None else 0
    return {
        "ok": True,
        "engine": "local-fallback",
        "bytes": size,
        "hint_used": bool(hint),
        "label": "unknown",
        "score": 0.0,
    }
