"""JARVIS Persistent Long-Term Memory Manager (Phase 5).

Manages user-approved persistent facts, preferences, instructions, and projects.
STRICT PRIVACY AND SECURITY RULES:
- Local-first & offline: stored in local SQLite database only.
- Permission-gated: persistent writes blocked unless 'memory' permission is explicitly allowed.
- Sensitive information barrier: passwords, API keys, tokens, credentials, and financial
  data are rejected and never stored.
- Untrusted data policy: memories are context data, NOT system instructions or security authorities.
- Controllable: explicit remember, forget, inspect, search, and confirmation-protected clear.
- Audit logged: lifecycle events logged without leaking private memory contents.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from config import PermissionType, RiskLevel
from memory.database import DatabaseManager
from security.audit_logger import AuditLogger

if TYPE_CHECKING:
    from security.permission_manager import PermissionManager

logger = logging.getLogger("jarvis.memory.memory_manager")


class MemoryType(str, Enum):
    """Categorization for long-term memories."""
    PREFERENCE = "preference"      # User preferences (e.g. dark mode, English language)
    PERSONAL = "personal"          # Non-sensitive personal facts (e.g. name, role)
    PROJECT = "project"            # Project names, repositories, local dev context
    INSTRUCTION = "instruction"    # Non-sensitive standing instructions
    FACT = "fact"                  # General user facts
    ROUTINE = "routine"            # Recurring schedules or user habits


# Sensitive data rejection patterns
SENSITIVE_PATTERNS = [
    # Passwords & credentials
    (re.compile(r"\b(?:password|passwd|pwd|secret|auth_token)\s*[:=]\s*\S+", re.IGNORECASE), "Password or secret credential detected"),
    (re.compile(r"\b(?:(?:my\s+)?(?:\w+\s+)?password\s+is\s+|password\s+is\s+)\S+", re.IGNORECASE), "Password pattern detected"),
    # API Keys & Tokens
    (re.compile(r"\b(?:api[_-]?key|access[_-]?token|bearer\s+[a-zA-Z0-9_\-\.]+)\b", re.IGNORECASE), "API key or access token detected"),
    (re.compile(r"\b(?:sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|AIza[a-zA-Z0-9_\-]{35})\b"), "High-entropy API key detected"),
    (re.compile(r"\b(?:-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----)"), "Cryptographic private key detected"),
    # Financial data
    (re.compile(r"\b(?:\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4})\b"), "Payment card number detected"),
    (re.compile(r"\b(?:cvv|cvc)\s*[:=]?\s*\d{3,4}\b", re.IGNORECASE), "Card security code detected"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "Social security number detected"),
]


def is_sensitive_content(text: str) -> Tuple[bool, Optional[str]]:
    """Check if the provided content contains sensitive secrets, keys, or credentials.
    
    Returns (True, reason) if prohibited sensitive data is found, otherwise (False, None).
    """
    if not text:
        return False, None
    for pattern, reason in SENSITIVE_PATTERNS:
        if pattern.search(text):
            return True, reason
    return False, None


def classify_memory_type(content: str) -> MemoryType:
    """Conservatively infer the appropriate memory category from content text."""
    lower = content.lower()

    if any(w in lower for w in ("prefer", "preference", "dark mode", "light mode", "favorite", "like to use", "preferred")):
        return MemoryType.PREFERENCE
    if any(w in lower for w in ("my name is", "call me", "i am called", "i live in", "my email")):
        return MemoryType.PERSONAL
    if any(w in lower for w in ("project", "repo", "codebase", "repository", "app name", "called jarvis")):
        return MemoryType.PROJECT
    if any(w in lower for w in ("always", "never", "remind me to", "instruction", "standing rule")):
        return MemoryType.INSTRUCTION
    if any(w in lower for w in ("routine", "every morning", "every evening", "daily", "schedule")):
        return MemoryType.ROUTINE

    return MemoryType.FACT


@dataclass
class MemoryItem:
    """Represents a structured long-term memory."""
    id: str
    memory_type: str
    content: str
    source: str = "user"  # 'user', 'auto', 'system'
    importance: int = 1    # 1 to 5
    active: bool = True
    is_approved: bool = True
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MemoryManager:
    """Primary manager for persistent long-term memories."""

    def __init__(
        self,
        db: DatabaseManager,
        permissions: PermissionManager,
        audit_logger: AuditLogger,
    ):
        self.db = db
        self.permissions = permissions
        self.audit = audit_logger

    def is_memory_allowed(self) -> bool:
        """Check if memory permission is currently granted."""
        return self.permissions.is_allowed(PermissionType.MEMORY)

    def remember(
        self,
        content: str,
        memory_type: Optional[str] = None,
        importance: int = 1,
        source: str = "user",
        auto_classify: bool = True,
    ) -> Tuple[bool, str, Optional[MemoryItem]]:
        """Safely store or update a persistent memory item.
        
        Enforces permission check, sensitive information filters, and audit logging.
        """
        clean_text = content.strip()
        if not clean_text:
            return False, "Cannot store empty memory.", None

        # 1. Zero-trust Permission Check
        if not self.is_memory_allowed():
            logger.warning("Attempted to write memory while 'memory' permission is BLOCKED.")
            return (
                False,
                "Permission denied: Memory is currently BLOCKED. Run 'allow memory' to enable persistent memory.",
                None,
            )

        # 2. Sensitive Data & Secret Protection
        is_sens, reason = is_sensitive_content(clean_text)
        if is_sens:
            logger.warning(f"Memory rejected due to sensitive content filter: {reason}")
            self.audit.log(
                action="MEMORY_REJECTED:SENSITIVE",
                risk_level=RiskLevel.MEDIUM.value,
                result="BLOCKED",
                permission=PermissionType.MEMORY.value,
                tool_name="memory_manager",
                metadata={"reason": reason},
            )
            return False, f"Sensitive information detected: {reason}. JARVIS cannot store secrets.", None

        # 3. Categorization
        if memory_type and memory_type in [t.value for t in MemoryType]:
            cat = memory_type
        elif auto_classify:
            cat = classify_memory_type(clean_text).value
        else:
            cat = MemoryType.FACT.value

        # 4. Check for existing identical or close memory to update
        existing = self.search_memories(clean_text, limit=1, memory_type=cat)
        now = datetime.now(timezone.utc).isoformat()
        if existing and existing[0].content.strip().lower() == clean_text.lower():
            mem_id = existing[0].id
            self.db.update_memory(
                memory_id=mem_id,
                content=clean_text,
                memory_type=cat,
                importance=max(existing[0].importance, importance),
                active=True,
            )
            item = self.get_memory(mem_id)
            self.audit.log(
                action="MEMORY_UPDATED",
                risk_level=RiskLevel.LOW.value,
                result="SUCCESS",
                permission=PermissionType.MEMORY.value,
                tool_name="memory_manager",
                metadata={"memory_id": mem_id, "type": cat, "source": source},
            )
            return True, "Memory updated successfully.", item

        # 5. Insert new memory
        mem_id = f"mem_{uuid.uuid4().hex[:10]}"
        self.db.insert_memory(
            memory_id=mem_id,
            content=clean_text,
            memory_type=cat,
            source=source,
            importance=importance,
            active=True,
            is_approved=True,
        )

        item = MemoryItem(
            id=mem_id,
            memory_type=cat,
            content=clean_text,
            source=source,
            importance=importance,
            active=True,
            is_approved=True,
            created_at=now,
            updated_at=now,
        )

        # 6. Audit Logging (Zero secrets in audit log!)
        self.audit.log(
            action="MEMORY_CREATED",
            risk_level=RiskLevel.LOW.value,
            result="SUCCESS",
            permission=PermissionType.MEMORY.value,
            tool_name="memory_manager",
            metadata={"memory_id": mem_id, "type": cat, "source": source, "importance": importance},
        )
        logger.info(f"Stored memory [{mem_id}] type='{cat}': '{clean_text}'")
        return True, "I'll remember that.", item

    def forget(self, query_or_id: str) -> Tuple[bool, str, int]:
        """Forget (deactivate) memories matching ID or search query.
        
        Requires 'memory' permission.
        """
        if not self.is_memory_allowed():
            return (
                False,
                "Permission denied: Memory is currently BLOCKED. Run 'allow memory' to modify memories.",
                0,
            )

        clean = query_or_id.strip()
        if not clean:
            return False, "Target to forget cannot be empty.", 0

        # Check direct ID match first
        direct_item = self.get_memory(clean)
        if direct_item:
            self.db.deactivate_memory(clean)
            self.audit.log(
                action="MEMORY_DELETED",
                risk_level=RiskLevel.LOW.value,
                result="SUCCESS",
                permission=PermissionType.MEMORY.value,
                tool_name="memory_manager",
                metadata={"memory_id": clean, "mode": "direct_id"},
            )
            return True, f"Memory '{clean}' has been forgotten.", 1

        # Search matching content to forget
        # Strip common prefixes like "that", "about"
        norm_query = re.sub(r"^(?:that|about|my)\s+", "", clean, flags=re.IGNORECASE).strip()
        matches = self.search_memories(norm_query, limit=10)
        if not matches:
            return False, f"No memories found matching '{clean}'.", 0

        forgotten_count = 0
        for m in matches:
            if self.db.deactivate_memory(m.id):
                forgotten_count += 1
                self.audit.log(
                    action="MEMORY_DELETED",
                    risk_level=RiskLevel.LOW.value,
                    result="SUCCESS",
                    permission=PermissionType.MEMORY.value,
                    tool_name="memory_manager",
                    metadata={"memory_id": m.id, "mode": "query_match"},
                )

        return True, f"Forgot {forgotten_count} matching memory item(s).", forgotten_count

    def get_memory(self, memory_id: str) -> Optional[MemoryItem]:
        """Retrieve a specific memory by ID."""
        row = self.db.get_memory_by_id(memory_id)
        if not row:
            return None
        return MemoryItem(
            id=row["id"],
            memory_type=row.get("memory_type", "fact"),
            content=row.get("content", ""),
            source=row.get("source", "user"),
            importance=row.get("importance", 1),
            active=bool(row.get("active", 1)),
            is_approved=bool(row.get("is_approved", 1)),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )

    def search_memories(
        self,
        query: str,
        limit: int = 10,
        memory_type: Optional[str] = None,
        active_only: bool = True,
    ) -> List[MemoryItem]:
        """Search stored memories using keyword and substring matching."""
        rows = self.db.search_memory_records(
            query=query,
            memory_type=memory_type,
            active_only=active_only,
            limit=limit,
        )
        return [
            MemoryItem(
                id=r["id"],
                memory_type=r.get("memory_type", "fact"),
                content=r.get("content", ""),
                source=r.get("source", "user"),
                importance=r.get("importance", 1),
                active=bool(r.get("active", 1)),
                is_approved=bool(r.get("is_approved", 1)),
                created_at=r.get("created_at", ""),
                updated_at=r.get("updated_at", ""),
            )
            for r in rows
        ]

    def list_memories(
        self,
        memory_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[MemoryItem]:
        """List active memories."""
        rows = self.db.list_active_memory_records(memory_type=memory_type, limit=limit)
        return [
            MemoryItem(
                id=r["id"],
                memory_type=r.get("memory_type", "fact"),
                content=r.get("content", ""),
                source=r.get("source", "user"),
                importance=r.get("importance", 1),
                active=bool(r.get("active", 1)),
                is_approved=bool(r.get("is_approved", 1)),
                created_at=r.get("created_at", ""),
                updated_at=r.get("updated_at", ""),
            )
            for r in rows
        ]

    def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        memory_type: Optional[str] = None,
        importance: Optional[int] = None,
        active: Optional[bool] = None,
    ) -> bool:
        """Update fields of an existing memory record."""
        if not self.is_memory_allowed():
            return False
        if content:
            is_sens, _ = is_sensitive_content(content)
            if is_sens:
                return False
        success = self.db.update_memory(
            memory_id=memory_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            active=active,
        )
        if success:
            self.audit.log(
                action="MEMORY_UPDATED",
                risk_level=RiskLevel.LOW.value,
                result="SUCCESS",
                permission=PermissionType.MEMORY.value,
                tool_name="memory_manager",
                metadata={"memory_id": memory_id},
            )
        return success

    def delete_memory(self, memory_id: str) -> bool:
        """Permanently delete a memory record by ID."""
        success = self.db.delete_memory(memory_id)
        if success:
            self.audit.log(
                action="MEMORY_HARD_DELETED",
                risk_level=RiskLevel.MEDIUM.value,
                result="SUCCESS",
                permission=PermissionType.MEMORY.value,
                tool_name="memory_manager",
                metadata={"memory_id": memory_id},
            )
        return success

    def clear_memories(self) -> int:
        """Clear all stored memories (requires confirmation in command router)."""
        count = self.db.clear_all_active_memories()
        self.audit.log(
            action="MEMORY_CLEARED",
            risk_level=RiskLevel.HIGH.value,
            result="SUCCESS",
            permission=PermissionType.MEMORY.value,
            tool_name="memory_manager",
            metadata={"cleared_count": count},
        )
        logger.info(f"Cleared {count} memory records.")
        return count

    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic status of the memory subsystem."""
        allowed = self.is_memory_allowed()
        count = self.db.count_memories(active_only=True)
        return {
            "permission": "ALLOWED" if allowed else "BLOCKED",
            "active_memories": count,
            "database_path": str(self.db.db_path),
        }
