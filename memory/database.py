"""JARVIS SQLite Database Layer.

Provides local persistent storage for:
- Users & preferences
- Conversations & messages
- Memories (user-approved)
- Permissions state (persisted)
- Registered tools
- Audit trail
- Scheduled tasks

Uses SQLite WAL mode for concurrency and strict foreign key integrity.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger("jarvis.database")

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    session_id TEXT UNIQUE,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    sender TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS conversation_messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    memory_type TEXT NOT NULL DEFAULT 'fact',
    content TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'user',
    importance INTEGER NOT NULL DEFAULT 1,
    active INTEGER NOT NULL DEFAULT 1,
    is_approved INTEGER NOT NULL DEFAULT 1,
    key TEXT DEFAULT '',
    value TEXT DEFAULT '',
    category TEXT DEFAULT 'general',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_active ON memories(active);
CREATE INDEX IF NOT EXISTS idx_conv_messages_session ON conversation_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_conv_messages_time ON conversation_messages(timestamp);

CREATE TABLE IF NOT EXISTS permissions (
    name TEXT PRIMARY KEY,
    status TEXT NOT NULL, -- 'allowed' or 'blocked'
    updated_at TEXT NOT NULL,
    reason TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tools (
    name TEXT PRIMARY KEY,
    permission_required TEXT,
    risk_level TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    action TEXT NOT NULL,
    tool_name TEXT,
    permission TEXT,
    risk_level TEXT NOT NULL,
    confirmation_status TEXT NOT NULL,
    result TEXT NOT NULL,
    error_details TEXT,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    cron_or_time TEXT NOT NULL,
    payload TEXT NOT NULL,
    status TEXT NOT NULL, -- 'pending', 'running', 'completed', 'cancelled'
    created_at TEXT NOT NULL
);
"""

DEFAULT_PERMISSIONS = [
    "microphone",
    "internet",
    "files",
    "screen",
    "pc_control",
    "automation",
    "cloud_ai",
    "web_access",
    "memory",
]


class DatabaseManager:
    """Manages SQLite database connections and core data persistence operations."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager yielding a SQLite connection configured for WAL and foreign keys."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=10.0,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON;")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        """Run schema migrations and initialize default permission states."""
        with self.get_connection() as conn:
            # 1. Pre-schema migration for existing database files: Ensure new columns exist before creating indexes
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memories'")
            if cursor.fetchone():
                col_cursor = conn.execute("PRAGMA table_info(memories)")
                existing_cols = {row["name"] for row in col_cursor.fetchall()}
                if "memory_type" not in existing_cols:
                    conn.execute("ALTER TABLE memories ADD COLUMN memory_type TEXT DEFAULT 'fact'")
                if "content" not in existing_cols:
                    conn.execute("ALTER TABLE memories ADD COLUMN content TEXT DEFAULT ''")
                if "source" not in existing_cols:
                    conn.execute("ALTER TABLE memories ADD COLUMN source TEXT DEFAULT 'user'")
                if "importance" not in existing_cols:
                    conn.execute("ALTER TABLE memories ADD COLUMN importance INTEGER DEFAULT 1")
                if "active" not in existing_cols:
                    conn.execute("ALTER TABLE memories ADD COLUMN active INTEGER DEFAULT 1")

            cursor_c = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'")
            if cursor_c.fetchone():
                col_c_cursor = conn.execute("PRAGMA table_info(conversations)")
                existing_c_cols = {row["name"] for row in col_c_cursor.fetchall()}
                if "session_id" not in existing_c_cols:
                    conn.execute("ALTER TABLE conversations ADD COLUMN session_id TEXT")

            # 2. Execute schema (creates any missing tables and indexes)
            conn.executescript(SCHEMA_SQL)

            # 3. Backfill content from value and memory_type from category if needed
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memories'")
            if cursor.fetchone():
                col_cursor = conn.execute("PRAGMA table_info(memories)")
                existing_cols = {row["name"] for row in col_cursor.fetchall()}
                if "value" in existing_cols and "content" in existing_cols:
                    conn.execute(
                        "UPDATE memories SET content = value WHERE (content IS NULL OR content = '') AND value IS NOT NULL AND value != ''"
                    )
                if "category" in existing_cols and "memory_type" in existing_cols:
                    conn.execute(
                        "UPDATE memories SET memory_type = category WHERE (memory_type IS NULL OR memory_type = 'fact') AND category IS NOT NULL AND category != 'general'"
                    )

            # 4. Seed default permissions if they don't already exist.
            # CRITICAL RULE: All default to 'blocked'.
            now = datetime.now(timezone.utc).isoformat()
            for perm in DEFAULT_PERMISSIONS:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO permissions (name, status, updated_at, reason)
                    VALUES (?, 'blocked', ?, 'System default: privacy-first')
                    """,
                    (perm, now),
                )
        logger.info(f"Database initialized at {self.db_path}")

    # =========================================================================
    # Permissions
    # =========================================================================

    def get_permission(self, name: str) -> Optional[Dict[str, Any]]:
        """Fetch permission status record."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT name, status, updated_at, reason FROM permissions WHERE name = ?",
                (name.lower(),)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_all_permissions(self) -> Dict[str, str]:
        """Return dict of {permission_name: status}."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT name, status FROM permissions")
            return {row["name"]: row["status"] for row in cursor.fetchall()}

    def set_permission(self, name: str, status: str, reason: str = "") -> None:
        """Update or insert permission status ('allowed' or 'blocked')."""
        status = status.lower()
        if status not in ("allowed", "blocked"):
            raise ValueError(f"Invalid status '{status}'. Must be 'allowed' or 'blocked'.")
        
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO permissions (name, status, updated_at, reason)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    status=excluded.status,
                    updated_at=excluded.updated_at,
                    reason=excluded.reason
                """,
                (name.lower(), status, now, reason),
            )

    # =========================================================================
    # Audit Logs
    # =========================================================================

    def insert_audit_log(self, entry: Any) -> int:
        """Insert an audit entry into the database."""
        meta_json = json.dumps(getattr(entry, "metadata", {}))
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO audit_logs (
                    timestamp, action, tool_name, permission,
                    risk_level, confirmation_status, result, error_details, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.timestamp,
                    entry.action,
                    entry.tool_name,
                    entry.permission,
                    entry.risk_level,
                    entry.confirmation_status,
                    entry.result,
                    entry.error_details,
                    meta_json,
                ),
            )
            return cursor.lastrowid or 0

    def get_recent_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent audit logs."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, timestamp, action, tool_name, permission,
                       risk_level, confirmation_status, result, error_details, metadata_json
                FROM audit_logs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Preferences
    # =========================================================================

    def get_preference(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Fetch a user preference value."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT value FROM preferences WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set_preference(self, key: str, value: str) -> None:
        """Set a user preference."""
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO preferences (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    updated_at=excluded.updated_at
                """,
                (key, value, now),
            )

    # =========================================================================
    # Memories (Local & Approved)
    # =========================================================================

    def save_memory(self, memory_id: str, key: str, value: str, category: str = "general", is_approved: bool = True) -> None:
        """Save a new memory (legacy & Phase 5 compatible)."""
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO memories (id, memory_type, content, source, importance, active, is_approved, key, value, category, created_at, updated_at)
                VALUES (?, ?, ?, 'user', 1, 1, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    memory_type=excluded.memory_type,
                    content=excluded.content,
                    key=excluded.key,
                    value=excluded.value,
                    category=excluded.category,
                    is_approved=excluded.is_approved,
                    active=1,
                    updated_at=excluded.updated_at
                """,
                (memory_id, category, value, 1 if is_approved else 0, key, value, category, now, now),
            )

    def insert_memory(
        self,
        memory_id: str,
        content: str,
        memory_type: str = "fact",
        source: str = "user",
        importance: int = 1,
        active: bool = True,
        is_approved: bool = True,
        key: str = "",
    ) -> None:
        """Insert or replace a Phase 5 memory record."""
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO memories (id, memory_type, content, source, importance, active, is_approved, key, value, category, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    memory_type=excluded.memory_type,
                    content=excluded.content,
                    source=excluded.source,
                    importance=excluded.importance,
                    active=excluded.active,
                    is_approved=excluded.is_approved,
                    key=excluded.key,
                    value=excluded.value,
                    category=excluded.category,
                    updated_at=excluded.updated_at
                """,
                (
                    memory_id,
                    memory_type,
                    content,
                    source,
                    importance,
                    1 if active else 0,
                    1 if is_approved else 0,
                    key or content[:32],
                    content,
                    memory_type,
                    now,
                    now,
                ),
            )

    def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        memory_type: Optional[str] = None,
        importance: Optional[int] = None,
        active: Optional[bool] = None,
    ) -> bool:
        """Update fields of an existing memory record."""
        updates: List[str] = []
        params: List[Any] = []
        now = datetime.now(timezone.utc).isoformat()

        if content is not None:
            updates.append("content = ?")
            params.append(content)
            updates.append("value = ?")
            params.append(content)
        if memory_type is not None:
            updates.append("memory_type = ?")
            params.append(memory_type)
            updates.append("category = ?")
            params.append(memory_type)
        if importance is not None:
            updates.append("importance = ?")
            params.append(importance)
        if active is not None:
            updates.append("active = ?")
            params.append(1 if active else 0)

        if not updates:
            return False

        updates.append("updated_at = ?")
        params.append(now)
        params.append(memory_id)

        query = f"UPDATE memories SET {', '.join(updates)} WHERE id = ?"
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount > 0

    def get_memory_by_id(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Fetch memory record by ID."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, memory_type, content, source, importance, active, is_approved,
                       key, value, category, created_at, updated_at
                FROM memories
                WHERE id = ?
                """,
                (memory_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def search_memory_records(
        self,
        query: str,
        memory_type: Optional[str] = None,
        active_only: bool = True,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search memory records using parameterized LIKE queries."""
        sql = """
            SELECT id, memory_type, content, source, importance, active, is_approved,
                   created_at, updated_at
            FROM memories
            WHERE 1=1
        """
        params: List[Any] = []
        if active_only:
            sql += " AND active = 1"
        if memory_type:
            sql += " AND memory_type = ?"
            params.append(memory_type)
        if query.strip():
            sql += " AND (content LIKE ? OR key LIKE ?)"
            pattern = f"%{query.strip()}%"
            params.extend([pattern, pattern])

        sql += " ORDER BY importance DESC, updated_at DESC LIMIT ?"
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def list_active_memory_records(
        self,
        memory_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List active memory records ordered by importance and recency."""
        sql = """
            SELECT id, memory_type, content, source, importance, active, is_approved,
                   created_at, updated_at
            FROM memories
            WHERE active = 1
        """
        params: List[Any] = []
        if memory_type:
            sql += " AND memory_type = ?"
            params.append(memory_type)
        sql += " ORDER BY importance DESC, updated_at DESC LIMIT ?"
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def deactivate_memory(self, memory_id: str) -> bool:
        """Mark a memory inactive (soft delete)."""
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE memories SET active = 0, updated_at = ? WHERE id = ?",
                (now, memory_id),
            )
            return cursor.rowcount > 0

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a single memory by ID (hard delete)."""
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            return cursor.rowcount > 0

    def delete_all_memories(self) -> int:
        """Delete all stored memories."""
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM memories")
            return cursor.rowcount

    def clear_all_active_memories(self) -> int:
        """Mark all memories inactive or delete."""
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM memories")
            return cursor.rowcount

    def count_memories(self, active_only: bool = True) -> int:
        """Count memories in database."""
        sql = "SELECT COUNT(*) as cnt FROM memories"
        if active_only:
            sql += " WHERE active = 1"
        with self.get_connection() as conn:
            cursor = conn.execute(sql)
            row = cursor.fetchone()
            return row["cnt"] if row else 0

    def get_memories(self, category: Optional[str] = None, approved_only: bool = True) -> List[Dict[str, Any]]:
        """Fetch stored memories (legacy compatibility)."""
        query = "SELECT id, key, value, category, is_approved, created_at, updated_at FROM memories WHERE 1=1"
        params: List[Any] = []
        if approved_only:
            query += " AND is_approved = 1"
        if category:
            query += " AND (category = ? OR memory_type = ?)"
            params.extend([category, category])
        query += " ORDER BY updated_at DESC"
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Conversations & Conversation Messages (Phase 5)
    # =========================================================================

    def insert_conversation_session(self, session_id: str, title: str = "Default Conversation") -> None:
        """Create or update a conversation session."""
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO conversations (id, session_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    session_id=excluded.session_id,
                    title=excluded.title,
                    updated_at=excluded.updated_at
                """,
                (session_id, session_id, title, now, now),
            )

    def get_conversation_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Fetch conversation session metadata."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, session_id, title, created_at, updated_at FROM conversations WHERE session_id = ? OR id = ?",
                (session_id, session_id),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_conversation_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent conversation sessions."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, session_id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def insert_conversation_message(
        self,
        message_id: str,
        session_id: str,
        role: str,
        content: str,
        timestamp: Optional[str] = None,
    ) -> None:
        """Insert a conversation message into conversation_messages."""
        now = timestamp or datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO conversation_messages (id, session_id, role, content, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (message_id, session_id, role, content, now),
            )
            # Update session updated_at timestamp
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE session_id = ? OR id = ?",
                (now, session_id, session_id),
            )

    def get_conversation_messages(
        self,
        session_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent conversation messages for a session (chronological order)."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, session_id, role, content, timestamp
                FROM conversation_messages
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (session_id, limit),
            )
            rows = [dict(r) for r in cursor.fetchall()]
            rows.reverse()  # Return in chronological order
            return rows

    def count_conversation_messages(self, session_id: Optional[str] = None) -> int:
        """Count conversation messages."""
        sql = "SELECT COUNT(*) as cnt FROM conversation_messages"
        params: List[Any] = []
        if session_id:
            sql += " WHERE session_id = ?"
            params.append(session_id)
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            row = cursor.fetchone()
            return row["cnt"] if row else 0

    def clear_conversation_messages(self, session_id: Optional[str] = None) -> int:
        """Clear messages for a session or all sessions."""
        sql = "DELETE FROM conversation_messages"
        params: List[Any] = []
        if session_id:
            sql += " WHERE session_id = ?"
            params.append(session_id)
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.rowcount
