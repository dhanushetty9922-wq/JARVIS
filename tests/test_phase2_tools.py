"""Tests for JARVIS Phase 2 Safe PC Control Tools."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from config import PermissionType, RiskLevel, Settings
from core.assistant import JarvisAssistant
from core.command_router import CommandRouter
from tools.app_control import APPROVED_APPLICATIONS, OpenAppTool
from tools.file_manager import (
    FORBIDDEN_SYSTEM_PATHS,
    get_standard_user_folder,
    validate_path_safety,
)


@pytest.fixture
def phase2_env():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir).resolve()
        settings = Settings(
            data_dir=tmp_path / "data",
            db_path=tmp_path / "data" / "jarvis.db",
            log_dir=tmp_path / "data" / "logs",
            safe_mode=True,
        )
        assistant = JarvisAssistant(custom_settings=settings)
        router = CommandRouter(assistant)
        try:
            yield {
                "assistant": assistant,
                "router": router,
                "tmp_path": tmp_path,
            }
        finally:
            assistant.shutdown()


def test_phase2_tools_registered(phase2_env):
    """Verify that all Phase 2 tools are registered in the Tool Registry."""
    assistant: JarvisAssistant = phase2_env["assistant"]
    registry = assistant.registry

    expected_tools = [
        "system_status",
        "echo",
        "open_application",
        "list_approved_applications",
        "open_folder",
        "search_files",
        "create_folder",
        "create_text_file",
        "rename_file",
        "copy_file",
        "move_file",
    ]

    for tool_name in expected_tools:
        assert registry.has(tool_name), f"Expected tool '{tool_name}' was not registered."


@pytest.mark.asyncio
async def test_open_app_permission_denial(phase2_env):
    """Opening an application when pc_control is blocked must be denied."""
    assistant: JarvisAssistant = phase2_env["assistant"]
    assert not assistant.permissions.is_allowed(PermissionType.PC_CONTROL)

    result = await assistant.execute_tool("open_application", {"app_name": "notepad"})
    assert not result.success
    assert "Permission denied" in result.error
    assert "pc_control" in result.error


@pytest.mark.asyncio
async def test_open_app_allowlist_enforcement(phase2_env):
    """Opening an unapproved application must be strictly rejected even with permission."""
    assistant: JarvisAssistant = phase2_env["assistant"]
    assistant.permissions.allow(PermissionType.PC_CONTROL)

    # 1. Unapproved application
    result = await assistant.execute_tool("open_application", {"app_name": "powershell_malicious.exe"})
    assert not result.success
    assert "not in the approved application allowlist" in result.error

    # 2. Approved application mock launch (avoiding spawning real windows during test)
    with patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.pid = 1234
        mock_popen.return_value = mock_proc

        res_ok = await assistant.execute_tool("open_application", {"app_name": "notepad"})
        assert res_ok.success
        assert "Notepad" in res_ok.message
        assert res_ok.data["pid"] == 1234


@pytest.mark.asyncio
async def test_open_folder_permission_and_validation(phase2_env):
    """Test folder launcher permission check and valid folder resolution."""
    assistant: JarvisAssistant = phase2_env["assistant"]

    # 1. Blocked by default
    res_denied = await assistant.execute_tool("open_folder", {"folder_name": "downloads"})
    assert not res_denied.success
    assert "Permission denied" in res_denied.error

    # 2. Grant permission
    assistant.permissions.allow(PermissionType.FILES)

    # 3. Invalid folder
    res_invalid = await assistant.execute_tool("open_folder", {"folder_name": "system32"})
    assert not res_invalid.success
    assert "Unsupported folder" in res_invalid.error

    # 4. Valid folder with mocked os.startfile / explorer
    with patch("os.startfile", create=True) as mock_start:
        for f_name in ("desktop", "documents", "downloads"):
            res = await assistant.execute_tool("open_folder", {"folder_name": f_name})
            assert res.success
            assert f_name.capitalize() in res.message


def test_system_location_safety_check(phase2_env):
    """System folders like C:\\Windows and C:\\Program Files must be rejected."""
    # SystemRoot
    win_dir = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    is_safe, reason = validate_path_safety(win_dir / "System32" / "drivers")
    assert not is_safe
    assert "Access denied" in reason

    # Program Files
    prog_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    is_safe_pf, reason_pf = validate_path_safety(prog_files / "TestApp")
    assert not is_safe_pf
    assert "Access denied" in reason_pf


@pytest.mark.asyncio
async def test_safe_file_operations_lifecycle(phase2_env):
    """Test non-destructive file operations in approved user directories."""
    assistant: JarvisAssistant = phase2_env["assistant"]
    assistant.permissions.allow(PermissionType.FILES)
    tmp_path: Path = phase2_env["tmp_path"]

    work_dir = tmp_path / "sandbox"

    # 1. Create Folder
    res_mkdir = await assistant.execute_tool("create_folder", {"folder_path": str(work_dir)})
    assert res_mkdir.success
    assert work_dir.is_dir()

    # 2. Create Text File
    file_a = work_dir / "notes.txt"
    res_create = await assistant.execute_tool(
        "create_text_file",
        {"file_path": str(file_a), "content": "JARVIS safe test"},
    )
    assert res_create.success
    assert file_a.read_text(encoding="utf-8") == "JARVIS safe test"

    # 3. Attempt overwrite without flag should fail
    res_no_overwrite = await assistant.execute_tool(
        "create_text_file",
        {"file_path": str(file_a), "content": "New content", "overwrite": False},
    )
    assert not res_no_overwrite.success
    assert "already exists" in res_no_overwrite.error

    # 4. Copy File
    file_b = work_dir / "notes_copy.txt"
    res_copy = await assistant.execute_tool(
        "copy_file",
        {"source_path": str(file_a), "destination_path": str(file_b)},
    )
    assert res_copy.success
    assert file_b.is_file()
    assert file_b.read_text(encoding="utf-8") == "JARVIS safe test"

    # 5. Rename File
    res_rename = await assistant.execute_tool(
        "rename_file",
        {"source_path": str(file_b), "new_name": "renamed_notes.txt"},
    )
    assert res_rename.success
    renamed_file = work_dir / "renamed_notes.txt"
    assert renamed_file.is_file()
    assert not file_b.exists()

    # 6. Move File
    sub_dir = work_dir / "archive"
    await assistant.execute_tool("create_folder", {"folder_path": str(sub_dir)})
    moved_file = sub_dir / "renamed_notes.txt"

    res_move = await assistant.execute_tool(
        "move_file",
        {"source_path": str(renamed_file), "destination_path": str(moved_file)},
    )
    assert res_move.success
    assert moved_file.is_file()
    assert not renamed_file.exists()


@pytest.mark.asyncio
async def test_search_files_tool(phase2_env):
    """Test file search within approved locations."""
    assistant: JarvisAssistant = phase2_env["assistant"]
    assistant.permissions.allow(PermissionType.FILES)
    tmp_path: Path = phase2_env["tmp_path"]

    # Create dummy files
    dummy_py = tmp_path / "agent_test.py"
    dummy_py.write_text("print('test')", encoding="utf-8")

    # Search in test directory
    res = await assistant.execute_tool("search_files", {"query": "agent_test", "location": str(tmp_path)})
    assert res.success
    matches = res.data["results"]
    assert any("agent_test.py" in m["filename"] for m in matches)


@pytest.mark.asyncio
async def test_cli_router_phase2_shortcuts(phase2_env):
    """Test 'open' and 'find' CLI command shortcuts."""
    router: CommandRouter = phase2_env["router"]
    assistant: JarvisAssistant = phase2_env["assistant"]

    # 1. 'open Chrome' without permission fails
    res_app_blocked = await router.handle_command("open Chrome")
    assert "Permission denied" in res_app_blocked

    # 2. Allow pc_control and mock open Chrome
    await router.handle_command("allow pc_control")
    with patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.pid = 999
        mock_popen.return_value = mock_proc
        res_app_ok = await router.handle_command("open Chrome")
        assert "Success: Application 'Google Chrome' opened" in res_app_ok

    # 3. 'open Downloads' without files permission fails
    res_folder_blocked = await router.handle_command("open Downloads")
    assert "Permission denied" in res_folder_blocked

    # 4. Allow files and test open Downloads
    await router.handle_command("allow files")
    with patch("os.startfile", create=True):
        res_folder_ok = await router.handle_command("open Downloads")
        assert "Success: Opened Downloads folder" in res_folder_ok

    # 5. 'find python files'
    res_find = await router.handle_command("find python files")
    assert "Found" in res_find or "No files found" in res_find
