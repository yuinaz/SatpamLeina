from __future__ import annotations

# legacy vendor v1 adapter (removed)

class LegacyAdapterRemoved(Exception):
    pass

def chat(*args, **kwargs):
    raise LegacyAdapterRemoved("Legacy adapter removed. Use satpambot.ai.groq_client.")

def stream(*args, **kwargs):
    raise LegacyAdapterRemoved("Legacy adapter removed. Use satpambot.ai.groq_client.")
