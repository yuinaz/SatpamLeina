# DB helper (auto)
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/app.db")
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

class ActionLog(Base):
    __tablename__ = "action_logs"
    id = Column(Integer, primary_key=True)
    ts = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(String(32))
    guild_id = Column(String(32))
    action = Column(String(64))   # delete|ban|kick|ocr|url_sus|url_black|invite_nsfw|img_scam
    reason = Column(Text)
    extra = Column(JSON, nullable=True)

def init_db():
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)

def log_action(user_id: str, guild_id: str, action: str, reason: str = "", extra: dict = None):
    try:
        with SessionLocal() as s:
            s.add(ActionLog(user_id=user_id or "-", guild_id=guild_id or "-", action=action or "-", reason=reason or "", extra=extra or {}))
            s.commit()
    except Exception as e:
        print("[db] log_action failed:", e)
