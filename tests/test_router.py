"""Tests for JARVIS Command Router and Safe CLI commands."""

import tempfile
from pathlib import Path
import pytest

from config import Settings
from core.assistant import JarvisAssistant
from core.command_router import CommandRouter


@pytest.fixture
def cli_router():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        settings = Settings(
            data_dir=tmp_path,
            db_path=tmp_path / "test.db",
            log_dir=tmp_path / "logs",
            safe_mode=True,
        )
        assistant = JarvisAssistant(custom_settings=settings)
        router = CommandRouter(assistant)
        try:
            yield router, assistant
        finally:
            assistant.shutdown()


@pytest.mark.asyncio
async def test_router_status_command(cli_router):
    router, _ = cli_router
    out = await router.handle_command("status")
    assert "JARVIS System Status" in out
    assert "Operating Mode:" in out
    assert "Safe Mode:" in out


@pytest.mark.asyncio
async def test_router_permission_commands(cli_router):
    router, assistant = cli_router
    out = await router.handle_command("permissions")
    assert "JARVIS Permission Status" in out
    assert "microphone" in out

    # Allow
    allow_out = await router.handle_command("allow microphone")
    assert "ALLOWED" in allow_out
    assert assistant.permissions.is_allowed("microphone") is True

    # Block
    block_out = await router.handle_command("block microphone")
    assert "BLOCKED" in block_out
    assert assistant.permissions.is_allowed("microphone") is False

    # Block all
    block_all_out = await router.handle_command("block all")
    assert "ALL permissions have been BLOCKED" in block_all_out


@pytest.mark.asyncio
async def test_router_emergency_stop_commands(cli_router):
    router, assistant = cli_router
    res_stop = await router.handle_command("emergency stop")
    assert "EMERGENCY STOP ENGAGED" in res_stop
    assert assistant.security.emergency_stopped is True

    res_reset = await router.handle_command("reset emergency stop")
    assert "RESET" in res_reset
    assert assistant.security.emergency_stopped is False


@pytest.mark.asyncio
async def test_router_safe_mode_commands(cli_router):
    router, assistant = cli_router
    res_off = await router.handle_command("safe mode off")
    assert "Safe Mode DISABLED" in res_off
    assert assistant.security.safe_mode is False

    res_on = await router.handle_command("safe mode on")
    assert "Safe Mode ENABLED" in res_on
    assert assistant.security.safe_mode is True


@pytest.mark.asyncio
async def test_router_run_tool(cli_router):
    router, _ = cli_router
    res = await router.handle_command('run echo {"message": "Hello Jarvis"}')
    assert "Tool Execution Succeeded" in res
    assert "Hello Jarvis" in res


@pytest.mark.asyncio
async def test_router_audit_and_help(cli_router):
    router, _ = cli_router
    # Run a command to generate audit trail
    await router.handle_command('run echo {"message": "Audit test"}')
    audit_out = await router.handle_command("audit 5")
    assert "Recent Audit Entries" in audit_out

    help_out = await router.handle_command("help")
    assert "JARVIS Available Commands" in help_out
