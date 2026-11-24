"""JARVIS Short-Term Conversation Context Store (Phase 5).

Persists and retrieves multi-turn dialogue messages across sessions.
Maintains session-level boundaries and ensures conversational recency
without overloading RAM or AI context windows.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from memory.database import DatabaseManager

logger = logging.getLogger("jarvis.memory.conversation_store")


@dataclass
class ConversationMessage:
    """Represents a single message in a conversation session."""
    id: str
    session_id: str
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConversationSession:
    """Metadata for a conversation session."""
    id: str
    session_id: str
    title: str
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ConversationStore:
    """Manages short-term conversation context and message persistence."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def create_session(self, session_id: Optional[str] = None, title: str = "Active Session") -> str:
        """Create a new conversation session."""
        sid = session_id or f"sess_{uuid.uuid4().hex[:12]}"
        self.db.insert_conversation_session(sid, title)
        logger.info(f"Created conversation session: '{sid}' ('{title}')")
        return sid

    def get_or_create_session(self, session_id: Optional[str] = None, title: str = "Active Session") -> str:
        """Ensure a session exists, creating it if necessary."""
        if not session_id:
            return self.create_session(title=title)
        existing = self.db.get_conversation_session(session_id)
        if not existing:
            return self.create_session(session_id=session_id, title=title)
        return session_id

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        timestamp: Optional[str] = None,
    ) -> ConversationMessage:
        """Record a message in the active session."""
        # Ensure session exists
        self.get_or_create_session(session_id)
        msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        clean_content = content.strip()
        
        self.db.insert_conversation_message(
            message_id=msg_id,
            session_id=session_id,
            role=role,
            content=clean_content,
            timestamp=ts,
        )
        return ConversationMessage(
            id=msg_id,
            session_id=session_id,
            role=role,
            content=clean_content,
            timestamp=ts,
        )

    def get_recent_messages(self, session_id: str, limit: int = 10) -> List[ConversationMessage]:
        """Fetch the most recent messages in chronological order."""
        raw_rows = self.db.get_conversation_messages(session_id, limit=limit)
        return [
            ConversationMessage(
                id=r["id"],
                session_id=r["session_id"],
                role=r["role"],
                content=r["content"],
                timestamp=r["timestamp"],
            )
            for r in raw_rows
        ]

    def list_sessions(self, limit: int = 20) -> List[ConversationSession]:
        """List recent conversation sessions."""
        rows = self.db.list_conversation_sessions(limit=limit)
        return [
            ConversationSession(
                id=r["id"],
                session_id=r["session_id"],
                title=r["title"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    def count_messages(self, session_id: Optional[str] = None) -> int:
        """Count messages across a session or entire database."""
        return self.db.count_conversation_messages(session_id)

    def clear_session(self, session_id: str) -> int:
        """Clear all messages in a specific session."""
        count = self.db.clear_conversation_messages(session_id)
        logger.info(f"Cleared {count} messages from session '{session_id}'")
        return count

    def clear_all(self) -> int:
        """Clear all conversation messages."""
        count = self.db.clear_conversation_messages(session_id=None)
        logger.info(f"Cleared all {count} conversation messages")
        return count
