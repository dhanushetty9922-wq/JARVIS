"""JARVIS Privacy & Permission Manager.

Enforces zero-trust, privacy-first permission control.
Default state: ALL permissions are BLOCKED.
No capability requiring a permission can run unless explicitly granted by the user.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional
from config import PermissionType, RiskLevel
from memory.database import DatabaseManager
from security.audit_logger import AuditLogger

logger = logging.getLogger("jarvis.security.permissions")

# Minimum required permissions
VALID_PERMISSIONS = {p.value for p in PermissionType}


class PermissionError(Exception):
    """Raised when an operation attempts to run without required permission."""
    pass


class PermissionManager:
    """Manages system permissions and enforces strict privacy boundaries."""

    def __init__(self, db_manager: DatabaseManager, audit_logger: AuditLogger):
        self.db = db_manager
        self.audit = audit_logger
        self._cache: Dict[str, str] = {}
        self.reload()

    def reload(self) -> None:
        """Reload permissions from database, ensuring all valid permissions exist."""
        db_perms = self.db.get_all_permissions()
        for perm in VALID_PERMISSIONS:
            if perm not in db_perms:
                # Seed default blocked state
                self.db.set_permission(perm, "blocked", "System default: privacy-first")
                self._cache[perm] = "blocked"
            else:
                self._cache[perm] = db_perms[perm]

    def _normalize_name(self, permission: str | PermissionType) -> str:
        """Normalize permission name to string and validate."""
        name = permission.value if isinstance(permission, PermissionType) else str(permission).strip().lower()
        if name not in VALID_PERMISSIONS:
            raise ValueError(f"Unknown permission '{name}'. Valid permissions: {sorted(list(VALID_PERMISSIONS))}")
        return name

    def is_allowed(self, permission: str | PermissionType) -> bool:
        """Check if a specific permission is granted.
        
        Returns False if the permission is blocked or unknown.
        """
        try:
            name = self._normalize_name(permission)
            return self._cache.get(name, "blocked") == "allowed"
        except ValueError:
            return False

    def allow(self, permission: str | PermissionType, reason: str = "User explicit grant") -> bool:
        """Explicitly allow a permission."""
        name = self._normalize_name(permission)
        old_status = self._cache.get(name, "blocked")
        
        self.db.set_permission(name, "allowed", reason)
        self._cache[name] = "allowed"
        
        self.audit.log(
            action=f"PERMISSION_GRANT:{name}",
            risk_level=RiskLevel.MEDIUM.value,
            result="ALLOWED",
            permission=name,
            metadata={"old_status": old_status, "new_status": "allowed", "reason": reason},
        )
        logger.info(f"Permission '{name}' granted ({reason})")
        return True

    def block(self, permission: str | PermissionType, reason: str = "User explicit revocation") -> bool:
        """Explicitly block a permission."""
        name = self._normalize_name(permission)
        old_status = self._cache.get(name, "blocked")
        
        self.db.set_permission(name, "blocked", reason)
        self._cache[name] = "blocked"
        
        self.audit.log(
            action=f"PERMISSION_REVOKE:{name}",
            risk_level=RiskLevel.MEDIUM.value,
            result="BLOCKED",
            permission=name,
            metadata={"old_status": old_status, "new_status": "blocked", "reason": reason},
        )
        logger.info(f"Permission '{name}' revoked ({reason})")
        return True

    def block_all(self, reason: str = "User block all command") -> None:
        """Revoke and block all permissions immediately."""
        for perm in VALID_PERMISSIONS:
            self.db.set_permission(perm, "blocked", reason)
            self._cache[perm] = "blocked"
            
        self.audit.log(
            action="PERMISSION_BLOCK_ALL",
            risk_level=RiskLevel.HIGH.value,
            result="BLOCKED",
            metadata={"reason": reason},
        )
        logger.warning(f"All permissions revoked: {reason}")

    def get_status(self, permission: str | PermissionType) -> str:
        """Get status ('allowed' or 'blocked') of a permission."""
        name = self._normalize_name(permission)
        return self._cache.get(name, "blocked")

    def get_all_statuses(self) -> Dict[str, str]:
        """Return a mapping of all permissions and their current status."""
        return dict(self._cache)

    def list_allowed(self) -> List[str]:
        """Return a list of all currently permitted capabilities."""
        return [k for k, v in self._cache.items() if v == "allowed"]

    def list_blocked(self) -> List[str]:
        """Return a list of all currently blocked capabilities."""
        return [k for k, v in self._cache.items() if v == "blocked"]
