import os
import asyncpg

_DSN = os.getenv("RENDER_POSTGRES_URL") or os.getenv("DATABASE_URL")

_SQL_INIT = """
CREATE TABLE IF NOT EXISTS xp_progress (
  id TEXT PRIMARY KEY,
  total_xp BIGINT NOT NULL,
  level TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

async def _conn():
    if not _DSN:
        raise RuntimeError("DATABASE_URL/RENDER_POSTGRES_URL not set")
    return await asyncpg.connect(_DSN)

async def save(total: int, level: str, id: str = "global"):
    conn = await _conn()
    try:
        await conn.execute(_SQL_INIT)
        await conn.execute(
            """INSERT INTO xp_progress (id,total_xp,level)
               VALUES ($1,$2,$3)
               ON CONFLICT (id)
               DO UPDATE SET total_xp=EXCLUDED.total_xp,
                             level=EXCLUDED.level,
                             updated_at=NOW()""",
            id, int(total), str(level)
        )
    finally:
        await conn.close()

async def load(id: str = "global"):
    conn = await _conn()
    try:
        row = await conn.fetchrow(
            "SELECT total_xp, level FROM xp_progress WHERE id=$1", id
        )
        if row:
            return int(row["total_xp"]), str(row["level"])
        return None, None
    finally:
        await conn.close()
