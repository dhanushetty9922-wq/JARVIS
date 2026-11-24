"""Tests for JARVIS Privacy and Permission Manager."""

import tempfile
from pathlib import Path
import pytest

from config import PermissionType, RiskLevel, Settings
from memory.database import DatabaseManager
from security.audit_logger import AuditLogger
from security.permission_manager import PermissionManager, VALID_PERMISSIONS


@pytest.fixture
def temp_env():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_path = tmp_path / "test.db"
        log_dir = tmp_path / "logs"
        settings = Settings(
            data_dir=tmp_path,
            db_path=db_path,
            log_dir=log_dir,
            safe_mode=True,
        )
        db = DatabaseManager(db_path)
        audit = AuditLogger(log_dir, db)
        perms = PermissionManager(db, audit)
        yield {"settings": settings, "db": db, "audit": audit, "perms": perms}


def test_default_permissions_blocked(temp_env):
    """Zero-trust rule: All permissions MUST be blocked by default."""
    perms: PermissionManager = temp_env["perms"]
    statuses = perms.get_all_statuses()

    assert len(statuses) == len(VALID_PERMISSIONS)
    for perm_name, status in statuses.items():
        assert status == "blocked"
        assert not perms.is_allowed(perm_name)


def test_permission_granting(temp_env):
    """Test granting a permission."""
    perms: PermissionManager = temp_env["perms"]
    audit: AuditLogger = temp_env["audit"]

    assert not perms.is_allowed(PermissionType.MICROPHONE)
    result = perms.allow(PermissionType.MICROPHONE, "Testing microphone grant")

    assert result is True
    assert perms.is_allowed(PermissionType.MICROPHONE)
    assert perms.get_status(PermissionType.MICROPHONE) == "allowed"

    # Verify audit log recorded event
    entries = audit.get_recent_entries()
    assert any("PERMISSION_GRANT:microphone" in e.action for e in entries)


def test_permission_revocation(temp_env):
    """Test revoking a previously granted permission."""
    perms: PermissionManager = temp_env["perms"]

    perms.allow(PermissionType.INTERNET)
    assert perms.is_allowed(PermissionType.INTERNET)

    perms.block(PermissionType.INTERNET, "Testing revocation")
    assert not perms.is_allowed(PermissionType.INTERNET)
    assert perms.get_status(PermissionType.INTERNET) == "blocked"


def test_block_all(temp_env):
    """Test revoking all permissions at once."""
    perms: PermissionManager = temp_env["perms"]

    # Grant several permissions
    perms.allow(PermissionType.MICROPHONE)
    perms.allow(PermissionType.FILES)
    perms.allow(PermissionType.SCREEN)

    assert len(perms.list_allowed()) == 3

    perms.block_all("Emergency privacy lockdown")

    assert len(perms.list_allowed()) == 0
    assert len(perms.list_blocked()) == len(VALID_PERMISSIONS)
    for p in VALID_PERMISSIONS:
        assert not perms.is_allowed(p)


def test_invalid_permission_name(temp_env):
    """Test handling of invalid permission names."""
    perms: PermissionManager = temp_env["perms"]

    with pytest.raises(ValueError):
        perms.allow("arbitrary_unknown_permission")

    with pytest.raises(ValueError):
        perms.block("unknown_perm")

    assert perms.is_allowed("unknown_perm") is False
