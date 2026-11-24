"""JARVIS Application Control Tools (Phase 2).

Provides safe, controlled launching of pre-approved Windows applications.
STRICT SECURITY POLICY:
- Only applications explicitly registered in the APPROVED_APPLICATIONS allowlist can be launched.
- Arbitrary executable paths, shell scripts, and PowerShell execution strings are rejected.
- Requires 'pc_control' permission.
- Every launch is audited through the central Security Manager.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from config import PermissionType, RiskLevel
from tools.base_tool import BaseTool, EmptyParams, ToolResult

logger = logging.getLogger("jarvis.tools.app_control")

# -----------------------------------------------------------------------------
# Approved Application Allowlist
# -----------------------------------------------------------------------------

APPROVED_APPLICATIONS: Dict[str, Dict[str, Any]] = {
    "notepad": {
        "display_name": "Notepad",
        "executables": ["notepad.exe"],
    },
    "calculator": {
        "display_name": "Calculator",
        "executables": ["calc.exe"],
        "protocol": "calculator:",
    },
    "calc": {
        "display_name": "Calculator",
        "executables": ["calc.exe"],
        "protocol": "calculator:",
    },
    "explorer": {
        "display_name": "File Explorer",
        "executables": ["explorer.exe"],
    },
    "file explorer": {
        "display_name": "File Explorer",
        "executables": ["explorer.exe"],
    },
    "chrome": {
        "display_name": "Google Chrome",
        "executables": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            "chrome.exe",
        ],
    },
    "google chrome": {
        "display_name": "Google Chrome",
        "executables": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            "chrome.exe",
        ],
    },
    "edge": {
        "display_name": "Microsoft Edge",
        "executables": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            "msedge.exe",
        ],
        "protocol": "microsoft-edge:",
    },
    "microsoft edge": {
        "display_name": "Microsoft Edge",
        "executables": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            "msedge.exe",
        ],
        "protocol": "microsoft-edge:",
    },
    "vscode": {
        "display_name": "Visual Studio Code",
        "executables": [
            "code.cmd",
            "code.exe",
            str(Path.home() / "AppData" / "Local" / "Programs" / "Microsoft VS Code" / "Code.exe"),
            r"C:\Program Files\Microsoft VS Code\Code.exe",
        ],
    },
    "code": {
        "display_name": "Visual Studio Code",
        "executables": [
            "code.cmd",
            "code.exe",
            str(Path.home() / "AppData" / "Local" / "Programs" / "Microsoft VS Code" / "Code.exe"),
            r"C:\Program Files\Microsoft VS Code\Code.exe",
        ],
    },
    "terminal": {
        "display_name": "Windows Terminal",
        "executables": ["wt.exe"],
    },
    "cmd": {
        "display_name": "Command Prompt",
        "executables": ["cmd.exe"],
    },
    "taskmgr": {
        "display_name": "Task Manager",
        "executables": ["taskmgr.exe"],
    },
    "task manager": {
        "display_name": "Task Manager",
        "executables": ["taskmgr.exe"],
    },
}


class OpenAppParams(BaseModel):
    """Parameters for opening an approved application."""
    app_name: str = Field(description="Name or alias of the approved application (e.g. 'chrome', 'notepad', 'calculator', 'vscode', 'explorer').")


class OpenAppTool(BaseTool):
    """Safely opens an approved Windows application from the allowlist."""

    name = "open_application"
    description = "Opens an approved Windows application (Notepad, Calculator, Chrome, Edge, VS Code, File Explorer, Terminal) from the safe allowlist."
    input_schema = OpenAppParams
    required_permission = PermissionType.PC_CONTROL
    risk_level = RiskLevel.LOW

    async def run(self, app_name: str, **kwargs: Any) -> ToolResult:
        query = app_name.strip().lower()

        # Step 1: Validate against strict allowlist
        if query not in APPROVED_APPLICATIONS:
            available = sorted(list({app["display_name"] for app in APPROVED_APPLICATIONS.values()}))
            return ToolResult.fail(
                error=f"Application '{app_name}' is not in the approved application allowlist.",
                message=f"Access denied: '{app_name}' is not approved. Approved applications: {', '.join(available)}",
            )

        app_info = APPROVED_APPLICATIONS[query]
        display_name = app_info["display_name"]

        # Step 2: Resolve executable path safely
        resolved_exe: Optional[str] = None
        for candidate in app_info["executables"]:
            # Check absolute path
            cand_path = Path(candidate)
            if cand_path.is_file():
                resolved_exe = str(cand_path)
                break
            # Check system PATH
            found = shutil.which(candidate)
            if found:
                resolved_exe = found
                break

        # Step 3: Launch process safely (without shell=True)
        try:
            if resolved_exe:
                proc = subprocess.Popen([resolved_exe], shell=False)
                return ToolResult.ok(
                    message=f"Application '{display_name}' opened successfully.",
                    data={"app": display_name, "executable": resolved_exe, "pid": proc.pid},
                )

            # Fallback for Windows URI protocols (e.g. calculator: or msedge:)
            if "protocol" in app_info and hasattr(os, "startfile"):
                os.startfile(app_info["protocol"])
                return ToolResult.ok(
                    message=f"Application '{display_name}' launched via Windows protocol.",
                    data={"app": display_name, "protocol": app_info["protocol"]},
                )

            # Fallback for direct command name via os.startfile
            fallback_name = app_info["executables"][0]
            if hasattr(os, "startfile"):
                os.startfile(fallback_name)
                return ToolResult.ok(
                    message=f"Application '{display_name}' launched via Windows shell.",
                    data={"app": display_name, "target": fallback_name},
                )

            return ToolResult.fail(
                error=f"Could not locate executable for '{display_name}' on this system.",
                message=f"Application '{display_name}' is approved, but its executable was not found.",
            )

        except Exception as e:
            logger.error(f"Failed to launch application '{display_name}': {e}")
            return ToolResult.fail(
                error=str(e),
                message=f"Failed to launch '{display_name}': {e}",
            )


class ListApprovedAppsTool(BaseTool):
    """Lists all approved applications in the launcher allowlist."""

    name = "list_approved_applications"
    description = "Lists all approved applications that JARVIS is permitted to launch."
    input_schema = EmptyParams
    required_permission = None
    risk_level = RiskLevel.LOW

    async def run(self, **kwargs: Any) -> ToolResult:
        unique_apps = sorted(list({app["display_name"] for app in APPROVED_APPLICATIONS.values()}))
        return ToolResult.ok(
            message=f"Found {len(unique_apps)} approved applications.",
            data={"approved_applications": unique_apps},
        )
