#!/usr/bin/env python3
from typing import Any

def fake_answer(prompt: str, system: str | None = None) -> str:
    return "[FAKE-LLM] " + (prompt[:64] if prompt else "")

class _FakeLLM:
    def __init__(self, *, model: str = "stub", max_tokens: int = 256) -> None:
        self.model = model
        self.max_tokens = max_tokens
    async def answer(self, prompt: str, system: str | None = None) -> str:
        return fake_answer(prompt, system)

def ensure_guard_thresholds_sane(config: dict[str, Any] | None = None) -> bool: return True
def ensure_qna_channels_allowlisted(cfg: dict[str, Any] | None = None) -> bool: return True
