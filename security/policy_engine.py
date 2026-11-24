"""JARVIS Security Policy Engine.

Enforces zero-trust deterministic security policies:
1. Emergency Stop Policy: Rejects all actions when emergency stop is engaged.
2. Safe Mode Policy: Prevents execution of HIGH or CRITICAL risk tools when safe mode is ON.
3. Offline Mode Policy: Prohibits tools requiring network capabilities when operating offline.
4. Permission Policy: Validates that required permissions are explicitly allowed.
5. Confirmation Policy: Determines if single or double confirmation is required.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple
from config import OperatingMode, PermissionType, RiskLevel, Settings
from tools.base_tool import BaseTool

logger = logging.getLogger("jarvis.security.policy")

NETWORK_PERMISSIONS = {
    PermissionType.INTERNET,
    PermissionType.CLOUD_AI,
    PermissionType.WEB_ACCESS,
}


class PolicyDecision:
    """Represents the outcome of a policy evaluation."""
    def __init__(
        self,
        allowed: bool,
        reason: str,
        requires_confirmation: bool = False,
        requires_double_confirmation: bool = False,
    ):
        self.allowed = allowed
        self.reason = reason
        self.requires_confirmation = requires_confirmation
        self.requires_double_confirmation = requires_double_confirmation

    @classmethod
    def allow(
        cls,
        reason: str = "Policy check passed",
        requires_confirmation: bool = False,
        requires_double_confirmation: bool = False,
    ) -> PolicyDecision:
        return cls(True, reason, requires_confirmation, requires_double_confirmation)

    @classmethod
    def deny(cls, reason: str) -> PolicyDecision:
        return cls(False, reason, False, False)


class PolicyEngine:
    """Deterministic security policy evaluator."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def evaluate(
        self,
        tool: BaseTool,
        emergency_stopped: bool,
        safe_mode: bool,
        current_mode: OperatingMode,
        permission_is_allowed: bool,
    ) -> PolicyDecision:
        """Evaluate whether a tool can be executed given system state and policy."""

        # 1. Emergency Stop Check
        if emergency_stopped:
            return PolicyDecision.deny("Execution blocked: EMERGENCY STOP is active.")

        # 2. Safe Mode Check: HIGH and CRITICAL tools are forbidden in Safe Mode
        if safe_mode and tool.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            return PolicyDecision.deny(
                f"Execution blocked: Tool '{tool.name}' has {tool.risk_level.value} risk, "
                "which is prohibited while Safe Mode is enabled."
            )

        # 3. Offline Mode Check: Network-dependent tools are forbidden in OFFLINE mode
        if current_mode == OperatingMode.OFFLINE and tool.required_permission in NETWORK_PERMISSIONS:
            return PolicyDecision.deny(
                f"Execution blocked: Tool '{tool.name}' requires '{tool.required_permission.value}', "
                "which is strictly prohibited in OFFLINE mode."
            )

        # 4. Permission Check: Permission must be explicitly granted
        if tool.required_permission is not None and not permission_is_allowed:
            return PolicyDecision.deny(
                f"Permission denied: Tool '{tool.name}' requires permission '{tool.required_permission.value}', "
                "which is currently BLOCKED."
            )

        # 5. Risk Assessment & Confirmation Requirements
        req_single = tool.risk_level == RiskLevel.HIGH
        req_double = tool.risk_level == RiskLevel.CRITICAL

        return PolicyDecision.allow(
            reason="All policy requirements satisfied",
            requires_confirmation=req_single,
            requires_double_confirmation=req_double,
        )
