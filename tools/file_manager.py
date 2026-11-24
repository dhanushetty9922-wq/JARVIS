"""JARVIS Safe File Management and Folder Launcher Subsystem (Phase 2).

Provides safe, controlled, non-destructive file operations and folder launching.
SECURITY POLICIES:
- System directories (C:\\Windows, C:\\Program Files, C:\\System32, drive roots) are strictly protected.
- Operations are restricted to user folders (Desktop, Documents, Downloads, user profile, workspace).
- Path traversal tricks (../) are resolved and rejected if outside safe bounds.
- NO permanent deletion tools are implemented in Phase 2.
- Requires 'files' permission.
- All operations are logged through the central Security Manager.
"""

from __future__ import annotations

import fnmatch
import logging
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from config import PermissionType, RiskLevel
from tools.base_tool import BaseTool, EmptyParams, ToolResult

logger = logging.getLogger("jarvis.tools.file_manager")

# -----------------------------------------------------------------------------
# Protected System Roots
# -----------------------------------------------------------------------------

FORBIDDEN_SYSTEM_PATHS = [
    Path(os.environ.get("SystemRoot", r"C:\Windows")).resolve(),
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")).resolve(),
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")).resolve(),
    Path(os.environ.get("ProgramData", r"C:\ProgramData")).resolve(),
    Path(r"C:\Recovery").resolve(),
    Path(r"C:\$Recycle.Bin").resolve(),
]

SKIP_DIRECTORIES = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "appdata",
}


def get_standard_user_folder(folder_name: str) -> Optional[Path]:
    """Dynamically resolve standard Windows user folder without hard-coding username.
    
    Supports: desktop, documents, downloads.
    Handles OneDrive redirection automatically.
    """
    home = Path.home()
    key = folder_name.strip().lower()

    # Try Windows Registry User Shell Folders first
    try:
        import winreg
        sub_key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        reg_names = {
            "desktop": "Desktop",
            "documents": "Personal",
            "downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
        }
        if key in reg_names:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as k:
                val, _ = winreg.QueryValueEx(k, reg_names[key])
                expanded = os.path.expandvars(val)
                p = Path(expanded).resolve()
                if p.is_dir():
                    return p
    except Exception:
        pass

    # Dynamic filesystem fallback
    if key == "desktop":
        for cand in [home / "OneDrive" / "Desktop", home / "Desktop"]:
            if cand.is_dir():
                return cand.resolve()
    elif key == "documents":
        for cand in [home / "OneDrive" / "Documents", home / "Documents"]:
            if cand.is_dir():
                return cand.resolve()
    elif key == "downloads":
        cand = home / "Downloads"
        if cand.is_dir():
            return cand.resolve()

    return None


def get_allowed_user_roots() -> List[Path]:
    """Return all approved base user directories."""
    roots: List[Path] = []
    home = Path.home().resolve()
    roots.append(home)

    for folder_key in ("desktop", "documents", "downloads"):
        f = get_standard_user_folder(folder_key)
        if f and f not in roots:
            roots.append(f)

    # Current project workspace
    cwd = Path.cwd().resolve()
    if cwd not in roots:
        roots.append(cwd)

    return roots


def validate_path_safety(target_path: Path, allow_create_parent: bool = False) -> Tuple[bool, str]:
    """Validate that path is within allowed user roots and NOT in protected system paths."""
    resolved = target_path.resolve()

    # 1. Drive root protection (e.g. C:\ or D:\)
    if resolved.parent == resolved:
        return False, f"Access denied: Root directory '{resolved}' cannot be modified."

    # 2. Forbidden system directories check
    for sys_path in FORBIDDEN_SYSTEM_PATHS:
        try:
            if resolved == sys_path or resolved.is_relative_to(sys_path):
                return False, f"Access denied: Path '{resolved}' is inside protected system location '{sys_path}'."
        except AttributeError:
            # Fallback for Python < 3.9 if ever needed
            if str(resolved).lower().startswith(str(sys_path).lower()):
                return False, f"Access denied: Path '{resolved}' is inside protected system location '{sys_path}'."

    # 3. Check if path is within approved user roots
    allowed_roots = get_allowed_user_roots()
    is_under_allowed = False
    for root in allowed_roots:
        try:
            if resolved == root or resolved.is_relative_to(root):
                is_under_allowed = True
                break
        except AttributeError:
            if str(resolved).lower().startswith(str(root).lower()):
                is_under_allowed = True
                break

    if not is_under_allowed:
        return False, f"Access denied: Path '{resolved}' is outside approved user locations."

    return True, "Path is valid."


# -----------------------------------------------------------------------------
# 1. Folder Launcher Tool
# -----------------------------------------------------------------------------

class OpenFolderParams(BaseModel):
    """Parameters for opening a standard user folder."""
    folder_name: str = Field(description="Name of the standard user folder: 'desktop', 'documents', or 'downloads'.")


class OpenFolderTool(BaseTool):
    """Safely opens a standard user folder in Windows File Explorer."""

    name = "open_folder"
    description = "Safely opens a standard user folder (Desktop, Documents, Downloads) in Windows Explorer."
    input_schema = OpenFolderParams
    required_permission = PermissionType.FILES
    risk_level = RiskLevel.LOW

    async def run(self, folder_name: str, **kwargs: Any) -> ToolResult:
        key = folder_name.strip().lower()
        if key not in ("desktop", "documents", "downloads"):
            return ToolResult.fail(
                error=f"Unsupported folder '{folder_name}'.",
                message=f"Supported folders are: 'desktop', 'documents', 'downloads'.",
            )

        resolved = get_standard_user_folder(key)
        if not resolved or not resolved.is_dir():
            return ToolResult.fail(
                error=f"Directory for '{folder_name}' could not be located on this PC.",
                message=f"Folder '{folder_name}' was not found.",
            )

        try:
            if hasattr(os, "startfile"):
                os.startfile(str(resolved))
            else:
                subprocess.Popen(["explorer.exe", str(resolved)], shell=False)

            return ToolResult.ok(
                message=f"Opened {folder_name.capitalize()} folder in File Explorer.",
                data={"folder": folder_name.capitalize(), "path": str(resolved)},
            )
        except Exception as e:
            logger.error(f"Failed opening folder '{folder_name}': {e}")
            return ToolResult.fail(
                error=str(e),
                message=f"Failed to open '{folder_name}': {e}",
            )


# -----------------------------------------------------------------------------
# 2. Safe File Search Tool
# -----------------------------------------------------------------------------

class SearchFilesParams(BaseModel):
    """Parameters for safe file search."""
    query: str = Field(description="Search term, extension, or glob pattern (e.g. '*.py', 'report', '*.pdf').")
    location: str = Field(default="all", description="Search target scope: 'desktop', 'documents', 'downloads', 'workspace', or 'all'.")
    max_results: int = Field(default=25, ge=1, le=100, description="Maximum number of results to return.")


class SearchFilesTool(BaseTool):
    """Searches for files matching a pattern within user-approved folders."""

    name = "search_files"
    description = "Searches for files by pattern within approved user locations (Desktop, Documents, Downloads, Workspace). Does not search system directories."
    input_schema = SearchFilesParams
    required_permission = PermissionType.FILES
    risk_level = RiskLevel.LOW

    async def run(self, query: str, location: str = "all", max_results: int = 25, **kwargs: Any) -> ToolResult:
        query_pattern = query.strip()
        if not query_pattern:
            return ToolResult.fail(error="Search query cannot be empty.")

        # If user searched "python files", normalize to "*.py"
        clean_q = query_pattern.lower()
        if clean_q == "python files" or clean_q == "python":
            pattern = "*.py"
        elif clean_q == "pdf files" or clean_q == "pdf":
            pattern = "*.pdf"
        elif "*" not in query_pattern and "?" not in query_pattern:
            pattern = f"*{query_pattern}*"
        else:
            pattern = query_pattern

        # Determine target search roots
        search_dirs: List[Path] = []
        loc = location.strip().lower()
        if loc in ("desktop", "documents", "downloads"):
            f = get_standard_user_folder(loc)
            if f and f.is_dir():
                search_dirs.append(f)
        elif loc == "workspace":
            search_dirs.append(Path.cwd().resolve())
        elif loc == "all":
            for k in ("desktop", "documents", "downloads"):
                f = get_standard_user_folder(k)
                if f and f.is_dir() and f not in search_dirs:
                    search_dirs.append(f)
            cwd = Path.cwd().resolve()
            if cwd not in search_dirs:
                search_dirs.append(cwd)
        else:
            cand_p = Path(location)
            if cand_p.is_dir():
                is_safe, reason = validate_path_safety(cand_p)
                if is_safe:
                    search_dirs.append(cand_p.resolve())
                else:
                    return ToolResult.fail(error=reason, message=reason)
            else:
                return ToolResult.fail(
                    error=f"Invalid location '{location}'.",
                    message="Valid locations: 'desktop', 'documents', 'downloads', 'workspace', 'all', or an approved user directory path.",
                )

        matches: List[Dict[str, Any]] = []

        for root in search_dirs:
            try:
                for dirpath, dirnames, filenames in os.walk(str(root)):
                    # Skip hidden/noisy directories in place
                    dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRECTORIES and not d.startswith(".")]

                    for filename in filenames:
                        if fnmatch.fnmatch(filename.lower(), pattern.lower()):
                            full_path = Path(dirpath) / filename
                            try:
                                stat = full_path.stat()
                                matches.append({
                                    "filename": filename,
                                    "path": str(full_path),
                                    "size_kb": round(stat.st_size / 1024, 2),
                                    "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                                })
                            except Exception:
                                matches.append({"filename": filename, "path": str(full_path)})

                            if len(matches) >= max_results:
                                break
                    if len(matches) >= max_results:
                        break
            except Exception as e:
                logger.warning(f"Error reading directory {root}: {e}")

        return ToolResult.ok(
            message=f"Found {len(matches)} matching file(s) for pattern '{pattern}'.",
            data={"query": query, "pattern": pattern, "results": matches},
        )


# -----------------------------------------------------------------------------
# 3. Non-destructive File Operations
# -----------------------------------------------------------------------------

class CreateFolderParams(BaseModel):
    folder_path: str = Field(description="Full path or relative path of the new folder to create.")


class CreateFolderTool(BaseTool):
    """Safely creates a new folder in an approved user location."""

    name = "create_folder"
    description = "Safely creates a new folder in an approved user directory."
    input_schema = CreateFolderParams
    required_permission = PermissionType.FILES
    risk_level = RiskLevel.LOW

    async def run(self, folder_path: str, **kwargs: Any) -> ToolResult:
        p = Path(folder_path)
        is_safe, reason = validate_path_safety(p)
        if not is_safe:
            return ToolResult.fail(error=reason, message=reason)

        try:
            p.mkdir(parents=True, exist_ok=True)
            return ToolResult.ok(
                message=f"Folder created successfully at '{p.resolve()}'.",
                data={"created_path": str(p.resolve())},
            )
        except Exception as e:
            return ToolResult.fail(error=str(e), message=f"Failed to create folder: {e}")


class CreateTextFileParams(BaseModel):
    file_path: str = Field(description="Target path for the text file.")
    content: str = Field(default="", description="Optional initial text content.")
    overwrite: bool = Field(default=False, description="Whether to overwrite if file already exists.")


class CreateTextFileTool(BaseTool):
    """Safely creates a text file in an approved user location."""

    name = "create_text_file"
    description = "Safely creates a new text file with optional content in an approved user directory."
    input_schema = CreateTextFileParams
    required_permission = PermissionType.FILES
    risk_level = RiskLevel.MEDIUM

    async def run(self, file_path: str, content: str = "", overwrite: bool = False, **kwargs: Any) -> ToolResult:
        p = Path(file_path)
        is_safe, reason = validate_path_safety(p)
        if not is_safe:
            return ToolResult.fail(error=reason, message=reason)

        if p.exists() and not overwrite:
            return ToolResult.fail(
                error=f"File already exists at '{p.resolve()}'.",
                message="Target file exists. Set overwrite=True if replacement is intended.",
            )

        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return ToolResult.ok(
                message=f"File created successfully at '{p.resolve()}'.",
                data={"file_path": str(p.resolve()), "size_bytes": len(content.encode("utf-8"))},
            )
        except Exception as e:
            return ToolResult.fail(error=str(e), message=f"Failed to write file: {e}")


class RenameFileParams(BaseModel):
    source_path: str = Field(description="Current path of the file to rename.")
    new_name: str = Field(description="New file name (filename only, without directory path).")


class RenameFileTool(BaseTool):
    """Safely renames a file in place within approved user directories."""

    name = "rename_file"
    description = "Safely renames an existing file in place."
    input_schema = RenameFileParams
    required_permission = PermissionType.FILES
    risk_level = RiskLevel.MEDIUM

    async def run(self, source_path: str, new_name: str, **kwargs: Any) -> ToolResult:
        src = Path(source_path)
        if not src.exists():
            return ToolResult.fail(error=f"Source file '{source_path}' does not exist.")

        is_safe, reason = validate_path_safety(src)
        if not is_safe:
            return ToolResult.fail(error=reason, message=reason)

        # Ensure new_name has no path separators (prevent accidental moves)
        clean_new = Path(new_name).name
        if not clean_new or clean_new != new_name.strip():
            return ToolResult.fail(error="new_name must be a simple filename, not a path.")

        dest = src.parent / clean_new
        if dest.exists():
            return ToolResult.fail(error=f"A file with name '{clean_new}' already exists in that folder.")

        try:
            src.rename(dest)
            return ToolResult.ok(
                message=f"Renamed '{src.name}' to '{dest.name}'.",
                data={"old_path": str(src.resolve()), "new_path": str(dest.resolve())},
            )
        except Exception as e:
            return ToolResult.fail(error=str(e), message=f"Failed to rename file: {e}")


class CopyFileParams(BaseModel):
    source_path: str = Field(description="Path of file to copy.")
    destination_path: str = Field(description="Target destination path.")


class CopyFileTool(BaseTool):
    """Safely copies a file from one approved user location to another."""

    name = "copy_file"
    description = "Safely copies a file to an approved destination."
    input_schema = CopyFileParams
    required_permission = PermissionType.FILES
    risk_level = RiskLevel.LOW

    async def run(self, source_path: str, destination_path: str, **kwargs: Any) -> ToolResult:
        src = Path(source_path)
        dest = Path(destination_path)

        if not src.exists():
            return ToolResult.fail(error=f"Source file '{source_path}' does not exist.")

        is_safe_src, r_src = validate_path_safety(src)
        if not is_safe_src:
            return ToolResult.fail(error=r_src)

        is_safe_dest, r_dest = validate_path_safety(dest)
        if not is_safe_dest:
            return ToolResult.fail(error=r_dest)

        try:
            if dest.is_dir():
                target = dest / src.name
            else:
                target = dest
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
            return ToolResult.ok(
                message=f"Copied '{src.name}' to '{target.resolve()}'.",
                data={"source": str(src.resolve()), "destination": str(target.resolve())},
            )
        except Exception as e:
            return ToolResult.fail(error=str(e), message=f"Failed to copy file: {e}")


class MoveFileParams(BaseModel):
    source_path: str = Field(description="Path of file to move.")
    destination_path: str = Field(description="Target destination path.")


class MoveFileTool(BaseTool):
    """Safely moves a file between approved user locations."""

    name = "move_file"
    description = "Safely moves a file from an approved source to an approved destination."
    input_schema = MoveFileParams
    required_permission = PermissionType.FILES
    risk_level = RiskLevel.MEDIUM

    async def run(self, source_path: str, destination_path: str, **kwargs: Any) -> ToolResult:
        src = Path(source_path)
        dest = Path(destination_path)

        if not src.exists():
            return ToolResult.fail(error=f"Source file '{source_path}' does not exist.")

        is_safe_src, r_src = validate_path_safety(src)
        if not is_safe_src:
            return ToolResult.fail(error=r_src)

        is_safe_dest, r_dest = validate_path_safety(dest)
        if not is_safe_dest:
            return ToolResult.fail(error=r_dest)

        try:
            if dest.is_dir():
                target = dest / src.name
            else:
                target = dest
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(target))
            return ToolResult.ok(
                message=f"Moved '{src.name}' to '{target.resolve()}'.",
                data={"source": str(src.resolve()), "destination": str(target.resolve())},
            )
        except Exception as e:
            return ToolResult.fail(error=str(e), message=f"Failed to move file: {e}")
