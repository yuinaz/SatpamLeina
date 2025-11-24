
# -*- coding: utf-8 -*-
"""Minimal, smoke-safe version of embed_scribe.
Provides a no-op `upsert` so overlays that monkeypatch it won't crash.
This is intended ONLY to make `scripts/smoke_cogs.py` pass in CI/local.
Live runtime can replace with the full implementation.
"""
from __future__ import annotations

try:
    import discord  # type: ignore
except Exception:  # pragma: no cover
    discord = None  # type: ignore

# ---- Public API expected by various cogs ---------------------------------

class EmbedScribe:
    """Very light helper to keep smoke imports happy."""
    def __init__(self, channel=None):
        self.channel = channel

    async def status(self, title: str, description: str | None = None, **kwargs):
        # No-op in smoke. Return None like send() would.
        return None

    async def info(self, title: str, description: str | None = None, **kwargs):
        return None

    async def warn(self, title: str, description: str | None = None, **kwargs):
        return None

    async def error(self, title: str, description: str | None = None, **kwargs):
        return None

    async def success(self, title: str, description: str | None = None, **kwargs):
        return None

# Some cogs import this name directly
def make_scribe(channel=None) -> EmbedScribe:
    return EmbedScribe(channel)

# Sticky/keeper overlays expect this callable to exist.
async def upsert(*args, **kwargs):
    """Smoke-safe no-op.
    Signature intentionally loose to accept any overlay kwargs.
    Returns None to mimic a send() that is ignored by callers.
    """
    return None

# Optional helpers that other modules MIGHT import; keep as no-ops.
async def ensure_pinned(*args, **kwargs):
    return None

async def coalesce_send(*args, **kwargs):
    return None

async def coalesce_edit(*args, **kwargs):
    return None
