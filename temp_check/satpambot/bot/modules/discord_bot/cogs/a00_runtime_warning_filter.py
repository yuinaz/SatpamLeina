
"""
Overlay: runtime warning filter for smoke/test env.

Suppresses only this known smoke/test warning:
  RuntimeWarning: coroutine 'DummyBot.add_cog' was never awaited

Why: The smoke loader uses a DummyBot where .add_cog is a coroutine and
one legacy cog calls it at import-time. In real runtime this does not occur.
This keeps smoke logs clean without changing cog behavior.
"""
import warnings
import logging

warnings.filterwarnings(
    "ignore",
    message=r"coroutine 'DummyBot\.add_cog' was never awaited",
    category=RuntimeWarning,
)
logging.getLogger(__name__).info("[warn-filter] suppressed DummyBot.add_cog unawaited warning (smoke/test only).")
