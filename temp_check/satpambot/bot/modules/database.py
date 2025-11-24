from datetime import date
# modules/database.py
# Minimal SQLAlchemy setup for ban list logging

import os
import datetime as dt
from typing import List, Optional, Dict

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite path (env overrideable)
DB_PATH = os.getenv("BAN_DB_PATH", os.path.join("data", "banlist.db"))
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
Base = declarative_base()

# --- Ban list models ---
class BanListEntry(Base):
    __tablename__ = "ban_list_entry"
    id = Column(Integer, primary_key=True)
    ts = Column(DateTime, default=dt.datetime.utcnow, index=True, nullable=False)
    user_id = Column(String(64), index=True, nullable=False)
    guild_id = Column(String(64), index=True, nullable=True)
    reason = Column(Text, nullable=True)

class BanListState(Base):
    __tablename__ = "ban_list_state"
    channel_id = Column(String(64), primary_key=True)
    message_id = Column(String(64), nullable=True)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

# Create tables if not present
def _init_db():
    Base.metadata.create_all(bind=engine)

_init_db()

# --- Public API used by helpers/banlog.py ---
def add_ban_entry(user_id: str, guild_id: Optional[str] = None, reason: Optional[str] = None):
    """Insert a ban entry."""
    with SessionLocal() as s:
        ent = BanListEntry(user_id=str(user_id), guild_id=str(guild_id) if guild_id else None, reason=reason or None)
        s.add(ent)
        s.commit()
        return ent.id

def get_recent_bans(limit: int = 20) -> List[Dict]:
    with SessionLocal() as s:
        q = s.query(BanListEntry).order_by(BanListEntry.ts.desc()).limit(int(limit))
        return [
            {
                "id": r.id,
                "ts": (r.ts.replace(tzinfo=dt.timezone.utc)).isoformat(),
                "user_id": r.user_id,
                "guild_id": r.guild_id,
                "reason": r.reason,
            }
            for r in q.all()
        ]

def get_banlist_message_id(channel_id: str) -> Optional[str]:
    with SessionLocal() as s:
        st = s.query(BanListState).filter_by(channel_id=str(channel_id)).first()
        return st.message_id if st else None

def set_banlist_message_id(channel_id: str, message_id: str):
    with SessionLocal() as s:
        st = s.query(BanListState).filter_by(channel_id=str(channel_id)).first()
        if not st:
            st = BanListState(channel_id=str(channel_id), message_id=str(message_id))
            s.add(st)
        else:
            st.message_id = str(message_id)
        s.commit()



# ======================
# Simple Daily Stats API
# ======================
from sqlalchemy import Integer, Date, func

class DailyStats(Base):
    __tablename__ = "daily_stats"
    id = Column(Integer, primary_key=True)
    day = Column(Date, index=True, nullable=False)
    guild_id = Column(String(64), index=True, nullable=True)
    joins = Column(Integer, default=0, nullable=False)
    leaves = Column(Integer, default=0, nullable=False)
    commands_ok = Column(Integer, default=0, nullable=False)
    commands_err = Column(Integer, default=0, nullable=False)
    bans = Column(Integer, default=0, nullable=False)
    unbans = Column(Integer, default=0, nullable=False)

def init_stats_db():
    """Ensure stats table exists."""
    Base.metadata.create_all(bind=engine)

def _daterange_days(n=7):
    today = date.today()
    days = [(today - timedelta(days=i)) for i in range(n-1, -1, -1)]
    return days

def get_last_7_days():
    """Return list of ISO date strings for the last 7 days (old→new)."""
    return [d.isoformat() for d in _daterange_days(7)]

def get_stats_last_7_days(guild_id: str | None = None):
    """Return aggregated stats per day for last 7 days."""
    days = _daterange_days(7)
    with SessionLocal() as s:
        q = s.query(
            DailyStats.day,
            func.sum(DailyStats.joins).label("joins"),
            func.sum(DailyStats.leaves).label("leaves"),
            func.sum(DailyStats.commands_ok).label("commands_ok"),
            func.sum(DailyStats.commands_err).label("commands_err"),
            func.sum(DailyStats.bans).label("bans"),
            func.sum(DailyStats.unbans).label("unbans"),
        )
        if guild_id:
            q = q.filter(DailyStats.guild_id == str(guild_id))
        q = q.filter(DailyStats.day >= days[0]).group_by(DailyStats.day)
        rows = { r.day: {
            "day": r.day.isoformat(),
            "joins": int(r.joins or 0),
            "leaves": int(r.leaves or 0),
            "commands_ok": int(r.commands_ok or 0),
            "commands_err": int(r.commands_err or 0),
            "bans": int(r.bans or 0),
            "unbans": int(r.unbans or 0),
        } for r in q.all() }
    # fill missing days with zeros
    out = []
    for d in days:
        out.append(rows.get(d, {
            "day": d.isoformat(),
            "joins": 0, "leaves": 0, "commands_ok": 0, "commands_err": 0, "bans": 0, "unbans": 0
        }))
    return out

def get_stats_all_guilds():
    """Return simple totals across all time (or last 7 days) for dashboard."""
    with SessionLocal() as s:
        q = s.query(
            func.sum(DailyStats.joins).label("joins"),
            func.sum(DailyStats.leaves).label("leaves"),
            func.sum(DailyStats.commands_ok).label("commands_ok"),
            func.sum(DailyStats.commands_err).label("commands_err"),
            func.sum(DailyStats.bans).label("bans"),
            func.sum(DailyStats.unbans).label("unbans"),
        )
        r = q.one()
        return {
            "joins": int(r.joins or 0),
            "leaves": int(r.leaves or 0),
            "commands_ok": int(r.commands_ok or 0),
            "commands_err": int(r.commands_err or 0),
            "bans": int(r.bans or 0),
            "unbans": int(r.unbans or 0),
        }

def get_hourly_join_leave(guild_id: str | None = None, day: date | None = None):
    """Return 24 hours buckets with zeros (placeholder, extend if needed)."""
    # Placeholder: returns 24 zeroed buckets for quick dashboard rendering
    return [{"hour": h, "joins": 0, "leaves": 0} for h in range(24)]
