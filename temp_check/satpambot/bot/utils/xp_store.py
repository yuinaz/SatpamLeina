import os

def _choose():
    # Prefer Postgres if DSN provided and asyncpg is available
    dsn = os.getenv("RENDER_POSTGRES_URL") or os.getenv("DATABASE_URL")
    if dsn:
        try:
            from . import xp_store_postgres as impl
            return impl
        except Exception:
            pass
    # fallback to JSON
    from . import xp_store_json as impl
    return impl

_impl = _choose()

async def save(total: int, level: str, id: str = "global"):
    return await _impl.save(total, level, id)

async def load(id: str = "global"):
    return await _impl.load(id)
