"""Shared pytest fixtures for JARVIS test suite.

Fixes Python 3.13 Windows PermissionError in tempfile.TemporaryDirectory cleanup
by using a project-local scratch directory instead of the system %TEMP% folder.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest

from config import Settings

# Project-local scratch directory for test isolation
SCRATCH_ROOT = Path(__file__).parent.parent / "data" / "_test_scratch"


@pytest.fixture(scope="function")
def tmp_test_dir():
    """
    Create an isolated test directory under data/_test_scratch/<uuid>.
    This avoids the Python 3.13 + Windows PermissionError that occurs
    when tempfile.TemporaryDirectory() tries to clean up %TEMP% paths.
    The directory is removed after each test.
    """
    test_id = uuid.uuid4().hex[:12]
    test_dir = SCRATCH_ROOT / test_id
    test_dir.mkdir(parents=True, exist_ok=True)
    yield test_dir
    # Best-effort cleanup; ignore errors on Windows locked files
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def isolated_settings(tmp_test_dir: Path) -> Settings:
    """
    Return a Settings object pointing to an isolated test directory.
    Uses silent TTS and simulated STT to avoid audio hardware dependencies.
    """
    data_dir = tmp_test_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "logs").mkdir(parents=True, exist_ok=True)

    return Settings(
        data_dir=data_dir,
        db_path=data_dir / "jarvis.db",
        log_dir=data_dir / "logs",
        safe_mode=True,
        ai_enabled=True,
        ai_mode="local",
        ai_provider="local",
        wake_phrase="Jzt Jarvis",
        tts_provider="silent",
        stt_provider="simulated",
    )
