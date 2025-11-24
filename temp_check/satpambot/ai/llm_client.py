# -*- coding: utf-8 -*-
"""
Unified LLM entrypoint for SatpamBot (Groq-only, patched).
"""
from __future__ import annotations

from .groq_client import make_groq_client, GroqLLM

def make_client():
    cli = make_groq_client()
    return GroqLLM(cli)
