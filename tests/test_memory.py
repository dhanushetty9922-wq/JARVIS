"""Tests for JARVIS Memory and Database subsystem."""

import tempfile
from pathlib import Path
import pytest

from memory.database import DatabaseManager
from security.audit_logger import AuditEntry, AuditLogger


@pytest.fixture
def db():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_memory.db"
        yield DatabaseManager(db_path)


def test_database_table_initialization(db: DatabaseManager):
    """Verify all required tables are created during initialization."""
    with db.get_connection() as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row["name"] for row in cursor.fetchall()}

    expected_tables = {
        "users",
        "preferences",
        "conversations",
        "messages",
        "memories",
        "permissions",
        "tools",
        "audit_logs",
        "scheduled_tasks",
    }
    assert expected_tables.issubset(tables)


def test_preferences_storage(db: DatabaseManager):
    """Verify user preferences can be set, updated, and retrieved."""
    assert db.get_preference("theme") is None
    db.set_preference("theme", "dark")
    assert db.get_preference("theme") == "dark"

    # Update preference
    db.set_preference("theme", "matrix_green")
    assert db.get_preference("theme") == "matrix_green"


def test_memory_crud_operations(db: DatabaseManager):
    """Verify memory creation, filtering, and deletion."""
    db.save_memory(
        memory_id="mem_1",
        key="user_name",
        value="Dhanush",
        category="profile",
        is_approved=True,
    )
    db.save_memory(
        memory_id="mem_2",
        key="project",
        value="JARVIS",
        category="work",
        is_approved=True,
    )
    db.save_memory(
        memory_id="mem_3",
        key="unapproved_note",
        value="draft",
        category="scratch",
        is_approved=False,
    )

    # 1. Fetch only approved memories
    approved = db.get_memories(approved_only=True)
    assert len(approved) == 2
    keys = {m["key"] for m in approved}
    assert "user_name" in keys
    assert "project" in keys
    assert "unapproved_note" not in keys

    # 2. Filter by category
    profile_mem = db.get_memories(category="profile")
    assert len(profile_mem) == 1
    assert profile_mem[0]["value"] == "Dhanush"

    # 3. Delete single memory
    deleted = db.delete_memory("mem_1")
    assert deleted is True
    assert len(db.get_memories(category="profile")) == 0

    # 4. Clear all memories
    count = db.delete_all_memories()
    assert count >= 1
    assert len(db.get_memories(approved_only=False)) == 0


def test_audit_log_database_persistence(db: DatabaseManager):
    """Verify audit entries are properly stored in the audit_logs table."""
    entry = AuditEntry(
        action="TEST_ACTION",
        tool_name="test_tool",
        permission="files",
        risk_level="HIGH",
        confirmation_status="CONFIRMED",
        result="SUCCESS",
        metadata={"user": "admin"},
    )

    row_id = db.insert_audit_log(entry)
    assert row_id > 0

    logs = db.get_recent_audit_logs(limit=10)
    assert len(logs) >= 1
    recent = logs[0]
    assert recent["action"] == "TEST_ACTION"
    assert recent["tool_name"] == "test_tool"
    assert recent["risk_level"] == "HIGH"
    assert recent["result"] == "SUCCESS"
