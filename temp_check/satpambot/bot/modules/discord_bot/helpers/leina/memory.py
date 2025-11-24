# -*- coding: utf-8 -*-
from __future__ import annotations
import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

log = logging.getLogger(__name__)

@dataclass
class Memory:
    category: str
    content: str
    timestamp: float
    importance: int = 1
    tags: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "content": self.content,
            "timestamp": self.timestamp,
            "importance": self.importance,
            "tags": self.tags or []
        }

class LeinaMemoryDB:
    """Memory system for storing and retrieving Leina's experiences"""
    
    def __init__(self, db_path: str = "data/leina/memory.sqlite3"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    importance INTEGER DEFAULT 1,
                    tags TEXT,
                    UNIQUE(category, content)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON memories(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)")

    async def add_memory(self, memory: Memory) -> bool:
        """Add new memory with deduplication"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO memories 
                    (category, content, timestamp, importance, tags) 
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        memory.category,
                        memory.content,
                        memory.timestamp,
                        memory.importance,
                        json.dumps(memory.tags or [])
                    )
                )
            return True
        except Exception as e:
            log.error(f"Error adding memory: {e}")
            return False

    async def get_memories(self, 
                         category: str, 
                         limit: int = 5, 
                         min_importance: int = 0) -> List[Memory]:
        """Retrieve memories filtered by category and importance"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT category, content, timestamp, importance, tags 
                    FROM memories 
                    WHERE category = ? AND importance >= ?
                    ORDER BY importance DESC, timestamp DESC LIMIT ?
                    """,
                    (category, min_importance, limit)
                )
                return [
                    Memory(
                        category=row[0],
                        content=row[1],
                        timestamp=row[2],
                        importance=row[3],
                        tags=json.loads(row[4]) if row[4] else []
                    )
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            log.error(f"Error retrieving memories: {e}")
            return []

    async def update_importance(self, category: str, content: str, delta: int) -> bool:
        """Update memory importance score"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE memories 
                    SET importance = importance + ? 
                    WHERE category = ? AND content = ?
                    """,
                    (delta, category, content)
                )
            return True
        except Exception as e:
            log.error(f"Error updating importance: {e}")
            return False

    CATEGORIES = [
        "master_interactions",   # Interaksi dengan Master
        "learning_moments",      # Hal-hal yang dipelajari
        "character_growth",      # Perkembangan karakter
        "user_favorites",        # Interaksi favorit dengan users
        "command_patterns"       # Pattern penggunaan command
    ]