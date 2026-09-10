"""
PiClaw SQLite Memory Store.
Lightweight persistent key-value memory that survives reboots.
< 100 KB typical footprint. No vector DB required.
Operations: store, search, recall, update, forget, list.
"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("piclaw.memory")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    key        TEXT    NOT NULL,
    value      TEXT    NOT NULL,
    tags       TEXT    DEFAULT '',
    created_at REAL    NOT NULL,
    updated_at REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_key ON memory(key);
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts
    USING fts5(key, value, tags, content=memory, content_rowid=id);
CREATE TRIGGER IF NOT EXISTS memory_ai
    AFTER INSERT ON memory BEGIN
        INSERT INTO memory_fts(rowid, key, value, tags)
        VALUES (new.id, new.key, new.value, new.tags);
    END;
CREATE TRIGGER IF NOT EXISTS memory_ad
    AFTER DELETE ON memory BEGIN
        INSERT INTO memory_fts(memory_fts, rowid, key, value, tags)
        VALUES ('delete', old.id, old.key, old.value, old.tags);
    END;
CREATE TRIGGER IF NOT EXISTS memory_au
    AFTER UPDATE ON memory BEGIN
        INSERT INTO memory_fts(memory_fts, rowid, key, value, tags)
        VALUES ('delete', old.id, old.key, old.value, old.tags);
        INSERT INTO memory_fts(rowid, key, value, tags)
        VALUES (new.id, new.key, new.value, new.tags);
    END;
"""


class MemoryStore:
    """
    Thread-safe SQLite memory store.
    Uses FTS5 for fast full-text search across key/value/tags.
    """

    def __init__(self, db_path: Path):
        self._path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        log.info(f"[Memory] SQLite store opened: {db_path}")

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def store(self, key: str, value: Any, tags: str = "") -> int:
        """Store or update a memory entry. Returns rowid."""
        now = time.time()
        value_str = json.dumps(value) if not isinstance(value, str) else value
        # Upsert: update if key exists
        existing = self._get_by_key(key)
        if existing:
            self._conn.execute(
                "UPDATE memory SET value=?, tags=?, updated_at=? WHERE key=?",
                (value_str, tags, now, key),
            )
            self._conn.commit()
            log.debug(f"[Memory] Updated: {key}")
            return existing["id"]
        else:
            cur = self._conn.execute(
                "INSERT INTO memory (key, value, tags, created_at, updated_at) VALUES (?,?,?,?,?)",
                (key, value_str, tags, now, now),
            )
            self._conn.commit()
            log.debug(f"[Memory] Stored: {key}")
            return cur.lastrowid

    def recall(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a memory entry by exact key."""
        row = self._get_by_key(key)
        return self._row_to_dict(row) if row else None

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Full-text search across key, value, and tags."""
        try:
            # FTS5 search
            rows = self._conn.execute(
                """SELECT m.* FROM memory m
                   JOIN memory_fts f ON m.id = f.rowid
                   WHERE memory_fts MATCH ?
                   ORDER BY rank LIMIT ?""",
                (query, limit),
            ).fetchall()
        except Exception:
            # Fallback: LIKE search
            pat = f"%{query}%"
            rows = self._conn.execute(
                "SELECT * FROM memory WHERE key LIKE ? OR value LIKE ? ORDER BY updated_at DESC LIMIT ?",
                (pat, pat, limit),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def forget(self, key: str) -> bool:
        """Delete a memory entry by key."""
        cur = self._conn.execute("DELETE FROM memory WHERE key=?", (key,))
        self._conn.commit()
        deleted = cur.rowcount > 0
        if deleted:
            log.debug(f"[Memory] Forgotten: {key}")
        return deleted

    def forget_by_id(self, mem_id: int) -> bool:
        cur = self._conn.execute("DELETE FROM memory WHERE id=?", (mem_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def list_all(self, limit: int = 50) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM memory ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0]

    def close(self) -> None:
        self._conn.close()

    # ── Internals ─────────────────────────────────────────────────────────────

    def _get_by_key(self, key: str) -> Optional[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM memory WHERE key=?", (key,)
        ).fetchone()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        try:
            d["value"] = json.loads(d["value"])
        except (json.JSONDecodeError, TypeError):
            pass
        return d


# Global singleton
_store: Optional[MemoryStore] = None


def get_memory_store(db_path: Optional[Path] = None) -> MemoryStore:
    global _store
    if _store is None:
        if db_path is None:
            from piclaw.utils.config import MEMORY_DB
            db_path = MEMORY_DB
        _store = MemoryStore(db_path)
    return _store
