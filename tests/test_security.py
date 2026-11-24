"""Tests for JARVIS Central Security Manager, Policy Engine, and Confirmation Manager."""

import tempfile
from pathlib import Path
from typing import Any, Dict
import pytest
from pydantic import BaseModel, Field

from config import OperatingMode, PermissionType, RiskLevel, Settings
from memory.database import DatabaseManager
from security.audit_logger import AuditLogger
from security.confirmation_manager import ConfirmationManager
from security.permission_manager import PermissionManager
from security.security_manager import SecurityManager
from tools.base_tool import BaseTool, EmptyParams, ToolResult
from tools.registry import ToolRegistry


# -----------------------------------------------------------------------------
# Test Tools
# -----------------------------------------------------------------------------

class SimpleParam(BaseModel):
    num: int = Field(gt=0, description="Positive integer")


class LowTool(BaseTool):
    name = "test_low"
    description = "Low risk test tool"
    input_schema = SimpleParam
    required_permission = None
    risk_level = RiskLevel.LOW

    async def run(self, num: int, **kwargs: Any) -> ToolResult:
        return ToolResult.ok(message=f"Double is {num * 2}", data={"val": num * 2})


class HighTool(BaseTool):
    name = "test_high"
    description = "High risk test tool"
    input_schema = SimpleParam
    required_permission = PermissionType.FILES
    risk_level = RiskLevel.HIGH

    async def run(self, num: int, **kwargs: Any) -> ToolResult:
        return ToolResult.ok(message=f"High executed: {num}")


class CriticalTool(BaseTool):
    name = "test_critical"
    description = "Critical risk test tool"
    input_schema = SimpleParam
    required_permission = PermissionType.PC_CONTROL
    risk_level = RiskLevel.CRITICAL

    async def run(self, num: int, **kwargs: Any) -> ToolResult:
        return ToolResult.ok(message=f"Critical executed: {num}")


class NetworkTool(BaseTool):
    name = "test_network"
    description = "Tool requiring internet permission"
    input_schema = SimpleParam
    required_permission = PermissionType.INTERNET
    risk_level = RiskLevel.LOW

    async def run(self, num: int, **kwargs: Any) -> ToolResult:
        return ToolResult.ok(message="Network fetched")


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def sec_env():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db = DatabaseManager(tmp_path / "test.db")
        audit = AuditLogger(tmp_path / "logs", db)
        perms = PermissionManager(db, audit)
        confirmation = ConfirmationManager()
        registry = ToolRegistry()

        # Register test tools
        registry.register(LowTool())
        registry.register(HighTool())
        registry.register(CriticalTool())
        registry.register(NetworkTool())

        settings = Settings(
            data_dir=tmp_path,
            db_path=tmp_path / "test.db",
            log_dir=tmp_path / "logs",
            safe_mode=False,
            jarvis_mode=OperatingMode.OFFLINE,
        )

        sec = SecurityManager(
            settings=settings,
            permission_manager=perms,
            confirmation_manager=confirmation,
            audit_logger=audit,
            tool_registry=registry,
        )

        yield {
            "sec": sec,
            "perms": perms,
            "confirmation": confirmation,
            "registry": registry,
            "audit": audit,
        }


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unauthorized_unknown_tool(sec_env):
    """Attempting to run a tool not in the registry must fail."""
    sec: SecurityManager = sec_env["sec"]
    result = await sec.execute_tool("nonexistent_tool", {})
    assert not result.success
    assert "Unknown or unapproved tool" in result.error


@pytest.mark.asyncio
async def test_schema_validation_failure(sec_env):
    """Passing invalid arguments violating Pydantic schema must be caught before execution."""
    sec: SecurityManager = sec_env["sec"]
    
    # Missing required argument 'num'
    result1 = await sec.execute_tool("test_low", {})
    assert not result1.success
    assert "validation failed" in result1.message.lower()

    # 'num' must be > 0
    result2 = await sec.execute_tool("test_low", {"num": -5})
    assert not result2.success
    assert "greater than 0" in result2.error.lower()


@pytest.mark.asyncio
async def test_permission_denial(sec_env):
    """Tool requiring a blocked permission must be rejected."""
    sec: SecurityManager = sec_env["sec"]
    perms: PermissionManager = sec_env["perms"]

    # test_high requires 'files' which is blocked by default
    assert not perms.is_allowed(PermissionType.FILES)
    result = await sec.execute_tool("test_high", {"num": 10})
    assert not result.success
    assert "Permission denied" in result.error
    assert "files" in result.error


@pytest.mark.asyncio
async def test_safe_mode_enforcement(sec_env):
    """When Safe Mode is enabled, HIGH and CRITICAL tools must be blocked immediately."""
    sec: SecurityManager = sec_env["sec"]
    perms: PermissionManager = sec_env["perms"]

    # Grant permission first
    perms.allow(PermissionType.FILES)
    perms.allow(PermissionType.PC_CONTROL)

    sec.set_safe_mode(True)
    assert sec.safe_mode is True

    # High tool blocked by safe mode
    result_high = await sec.execute_tool("test_high", {"num": 10})
    assert not result_high.success
    assert "Safe Mode is enabled" in result_high.error

    # Critical tool blocked by safe mode
    result_crit = await sec.execute_tool("test_critical", {"num": 10})
    assert not result_crit.success
    assert "Safe Mode is enabled" in result_crit.error

    # Low tool permitted in safe mode
    result_low = await sec.execute_tool("test_low", {"num": 10})
    assert result_low.success


@pytest.mark.asyncio
async def test_emergency_stop_lifecycle(sec_env):
    """Emergency stop halts all operations; reset restores operation."""
    sec: SecurityManager = sec_env["sec"]

    sec.trigger_emergency_stop("Test emergency stop")
    assert sec.emergency_stopped is True

    # Even a LOW risk tool must be blocked
    result = await sec.execute_tool("test_low", {"num": 5})
    assert not result.success
    assert "emergency stop is active" in result.error.lower()

    # Reset
    sec.reset_emergency_stop()
    assert sec.emergency_stopped is False

    result_after = await sec.execute_tool("test_low", {"num": 5})
    assert result_after.success
    assert result_after.data["val"] == 10


@pytest.mark.asyncio
async def test_offline_mode_blocks_network_tools(sec_env):
    """In OFFLINE mode, network tools are prohibited even if permission was granted."""
    sec: SecurityManager = sec_env["sec"]
    perms: PermissionManager = sec_env["perms"]

    # Even if permission is granted
    perms.allow(PermissionType.INTERNET)
    sec.set_operating_mode(OperatingMode.OFFLINE)

    result = await sec.execute_tool("test_network", {"num": 1})
    assert not result.success
    assert "strictly prohibited in OFFLINE mode" in result.error

    # Switch to ONLINE mode -> should succeed
    sec.set_operating_mode(OperatingMode.ONLINE)
    result_online = await sec.execute_tool("test_network", {"num": 1})
    assert result_online.success


@pytest.mark.asyncio
async def test_single_confirmation_high_risk(sec_env):
    """High risk tool requires single confirmation."""
    sec: SecurityManager = sec_env["sec"]
    perms: PermissionManager = sec_env["perms"]
    conf: ConfirmationManager = sec_env["confirmation"]

    perms.allow(PermissionType.FILES)
    sec.set_safe_mode(False)

    # 1. User confirms
    conf.set_handler(lambda msg, step, total: True)
    res_ok = await sec.execute_tool("test_high", {"num": 42})
    assert res_ok.success

    # 2. User rejects
    conf.set_handler(lambda msg, step, total: False)
    res_reject = await sec.execute_tool("test_high", {"num": 42})
    assert not res_reject.success
    assert "not confirmed by user" in res_reject.error


@pytest.mark.asyncio
async def test_double_confirmation_critical_risk(sec_env):
    """Critical risk tool requires double confirmation."""
    sec: SecurityManager = sec_env["sec"]
    perms: PermissionManager = sec_env["perms"]
    conf: ConfirmationManager = sec_env["confirmation"]

    perms.allow(PermissionType.PC_CONTROL)
    sec.set_safe_mode(False)

    # Case 1: Confirms both step 1 and step 2
    steps_called = []
    def confirm_both(msg, step, total):
        steps_called.append(step)
        return True

    conf.set_handler(confirm_both)
    res1 = await sec.execute_tool("test_critical", {"num": 99})
    assert res1.success
    assert steps_called == [1, 2]

    # Case 2: Rejects at step 1
    conf.set_handler(lambda msg, step, total: False)
    res2 = await sec.execute_tool("test_critical", {"num": 99})
    assert not res2.success
    assert "not confirmed by user" in res2.error

    # Case 3: Confirms step 1, but rejects step 2
    def reject_at_step_2(msg, step, total):
        return step == 1

    conf.set_handler(reject_at_step_2)
    res3 = await sec.execute_tool("test_critical", {"num": 99})
    assert not res3.success
    assert "not confirmed by user" in res3.error
