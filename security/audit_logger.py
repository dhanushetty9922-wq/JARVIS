"""JARVIS Audit and Logging System.

Maintains strict, segregated logs for:
- Application events (app.log)
- Errors & exceptions (error.log)
- Security checks & blocks (security.log)
- Structured immutable audit records (audit.log & SQLite audit_logs table)

Ensures that secrets and sensitive information are NEVER logged.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Sensitive key masking regexes
SENSITIVE_PATTERNS = [
    re.compile(r'(api[-_]?key|password|secret|token|bearer|authorization)\s*[:=]\s*([\'"]?[^\s,\'"]+[\'"]?)', re.IGNORECASE),
]


def sanitize_text(text: str) -> str:
    """Mask sensitive tokens or passwords from string."""
    if not isinstance(text, str):
        text = str(text)
    sanitized = text
    for pattern in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(r'\1: [REDACTED]', sanitized)
    return sanitized


class AuditEntry(BaseModel):
    """Structured representation of an audit event."""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    action: str
    tool_name: Optional[str] = None
    permission: Optional[str] = None
    risk_level: str
    confirmation_status: str  # e.g., "NOT_REQUIRED", "PENDING", "CONFIRMED", "REJECTED", "DOUBLE_CONFIRMED"
    result: str                # e.g., "ALLOWED", "BLOCKED", "SUCCESS", "FAILED"
    error_details: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SanitizingFormatter(logging.Formatter):
    """Logging formatter that sanitizes secrets before emitting messages."""
    def format(self, record: logging.LogRecord) -> str:
        orig = super().format(record)
        return sanitize_text(orig)


def setup_logging(log_dir: Path, log_level: str = "INFO") -> None:
    """Configure structured, segregated logging handlers."""
    log_dir.mkdir(parents=True, exist_ok=True)
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    root_logger = logging.getLogger("jarvis")
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()

    formatter = SanitizingFormatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. Application log (app.log)
    app_handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(formatter)
    root_logger.addHandler(app_handler)

    # 2. Error log (error.log)
    err_handler = logging.FileHandler(log_dir / "error.log", encoding="utf-8")
    err_handler.setLevel(logging.WARNING)
    err_handler.setFormatter(formatter)
    root_logger.addHandler(err_handler)

    # 3. Security log (security.log)
    sec_logger = logging.getLogger("jarvis.security")
    sec_handler = logging.FileHandler(log_dir / "security.log", encoding="utf-8")
    sec_handler.setLevel(logging.INFO)
    sec_handler.setFormatter(formatter)
    sec_logger.addHandler(sec_handler)

    # Prevent security logs from duplicating unnecessarily if needed, but keep root propagation
    sec_logger.propagate = True


def close_logging() -> None:
    """Close and flush all open file handlers (critical for clean shutdowns on Windows)."""
    for logger_name in ("jarvis", "jarvis.security"):
        lg = logging.getLogger(logger_name)
        for h in list(lg.handlers):
            try:
                h.flush()
                h.close()
            except Exception:
                pass
            lg.removeHandler(h)


class AuditLogger:
    """Audit logger managing structured JSON-lines file and optional database storage."""

    def __init__(self, log_dir: Path, db_manager: Any = None):
        self.log_dir = log_dir
        self.db_manager = db_manager
        self.audit_file = log_dir / "audit.log"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.sec_logger = logging.getLogger("jarvis.security")

    def set_db_manager(self, db_manager: Any) -> None:
        """Inject database manager after initialization if needed."""
        self.db_manager = db_manager

    def log(
        self,
        action: str,
        risk_level: str,
        result: str,
        confirmation_status: str = "NOT_REQUIRED",
        tool_name: Optional[str] = None,
        permission: Optional[str] = None,
        error_details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """Record an audit event."""
        # Sanitize metadata
        clean_meta = {}
        if metadata:
            for k, v in metadata.items():
                if any(s in k.lower() for s in ("key", "pass", "token", "secret", "auth")):
                    clean_meta[k] = "[REDACTED]"
                else:
                    clean_meta[k] = sanitize_text(str(v)) if isinstance(v, str) else v

        clean_error = sanitize_text(error_details) if error_details else None

        entry = AuditEntry(
            action=action,
            tool_name=tool_name,
            permission=permission,
            risk_level=risk_level,
            confirmation_status=confirmation_status,
            result=result,
            error_details=clean_error,
            metadata=clean_meta,
        )

        # 1. Write to JSON-lines audit file
        try:
            with open(self.audit_file, "a", encoding="utf-8") as f:
                f.write(entry.model_dump_json() + "\n")
        except Exception as e:
            logging.getLogger("jarvis").error(f"Failed writing to audit.log: {e}")

        # 2. Write to Security Logger
        sec_msg = (
            f"ACTION={action} | RESULT={result} | RISK={risk_level} | "
            f"TOOL={tool_name} | PERM={permission} | CONFIRM={confirmation_status}"
        )
        if clean_error:
            sec_msg += f" | ERROR={clean_error}"
        self.sec_logger.info(sec_msg)

        # 3. Write to SQLite if database manager is available
        if self.db_manager:
            try:
                self.db_manager.insert_audit_log(entry)
            except Exception as e:
                logging.getLogger("jarvis").error(f"Failed inserting audit log to DB: {e}")

        return entry

    def get_recent_entries(self, limit: int = 20) -> List[AuditEntry]:
        """Read the most recent audit entries from file."""
        if not self.audit_file.exists():
            return []
        entries: List[AuditEntry] = []
        try:
            with open(self.audit_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines[-limit:]):
                    line = line.strip()
                    if line:
                        entries.append(AuditEntry.model_validate_json(line))
        except Exception as e:
            logging.getLogger("jarvis").error(f"Failed reading recent audit entries: {e}")
        return entries
