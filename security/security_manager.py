"""JARVIS Security Manager.

The central security gateway of JARVIS.
Guarantees that no tool can execute without:
1. Being registered in the approved Tool Registry
2. Validating arguments against its strict Pydantic input schema
3. Satisfying all Policy Engine rules (Emergency Stop, Safe Mode, Mode constraints)
4. Having explicit permission granted via the Permission Manager
5. Successfully acquiring interactive user confirmation if required
6. Emitting immutable structured audit log entries

The AI or user NEVER has direct arbitrary execution access.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from pydantic import ValidationError

from config import OperatingMode, RiskLevel, Settings
from security.audit_logger import AuditLogger
from security.confirmation_manager import ConfirmationManager
from security.permission_manager import PermissionManager
from security.policy_engine import PolicyDecision, PolicyEngine
from tools.base_tool import BaseTool, ToolResult
from tools.registry import ToolRegistry

logger = logging.getLogger("jarvis.security.manager")


class SecurityManager:
    """Central authority controlling tool execution, risk assessment, and system safety."""

    def __init__(
        self,
        settings: Settings,
        permission_manager: PermissionManager,
        confirmation_manager: ConfirmationManager,
        audit_logger: AuditLogger,
        tool_registry: ToolRegistry,
    ):
        self.settings = settings
        self.permissions = permission_manager
        self.confirmation = confirmation_manager
        self.audit = audit_logger
        self.registry = tool_registry
        self.policy_engine = PolicyEngine(settings)

        # Safety states
        self._emergency_stopped: bool = False
        self._safe_mode: bool = settings.safe_mode
        self._operating_mode: OperatingMode = settings.jarvis_mode

    @property
    def emergency_stopped(self) -> bool:
        return self._emergency_stopped

    @property
    def safe_mode(self) -> bool:
        return self._safe_mode

    @property
    def operating_mode(self) -> OperatingMode:
        return self._operating_mode

    def trigger_emergency_stop(self, reason: str = "Emergency stop requested") -> None:
        """Immediately trigger emergency stop, blocking all tool executions."""
        self._emergency_stopped = True
        logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")
        self.audit.log(
            action="EMERGENCY_STOP",
            risk_level=RiskLevel.CRITICAL.value,
            result="TRIGGERED",
            error_details=reason,
        )

    def reset_emergency_stop(self) -> None:
        """Reset emergency stop state after verified recovery."""
        self._emergency_stopped = False
        logger.info("Emergency stop has been RESET.")
        self.audit.log(
            action="EMERGENCY_STOP_RESET",
            risk_level=RiskLevel.HIGH.value,
            result="RESET",
        )

    def set_safe_mode(self, enabled: bool) -> None:
        """Enable or disable Safe Mode."""
        self._safe_mode = enabled
        status_str = "ENABLED" if enabled else "DISABLED"
        logger.info(f"Safe Mode is now {status_str}.")
        self.audit.log(
            action=f"SAFE_MODE_{status_str}",
            risk_level=RiskLevel.MEDIUM.value,
            result=status_str,
        )

    def set_operating_mode(self, mode: OperatingMode) -> None:
        """Switch operating mode (offline, hybrid, online)."""
        old_mode = self._operating_mode
        self._operating_mode = mode
        logger.info(f"Operating mode changed: {old_mode.value} -> {mode.value}")
        self.audit.log(
            action="OPERATING_MODE_CHANGE",
            risk_level=RiskLevel.MEDIUM.value,
            result=mode.value,
            metadata={"previous_mode": old_mode.value, "new_mode": mode.value},
        )

    async def execute_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> ToolResult:
        """Safely execute an approved tool through the complete security pipeline."""
        arguments = arguments or {}
        norm_name = tool_name.strip().lower()

        # Step 1: Emergency stop verification
        if self._emergency_stopped:
            msg = "Execution aborted: Emergency stop is active."
            self.audit.log(
                action=f"EXECUTE_TOOL:{norm_name}",
                tool_name=norm_name,
                risk_level=RiskLevel.CRITICAL.value,
                result="BLOCKED",
                error_details=msg,
            )
            return ToolResult.fail(error=msg, message="System is in emergency stop state.")

        # Step 2: Tool Registry validation
        tool = self.registry.get(norm_name)
        if not tool:
            msg = f"Unknown or unapproved tool: '{norm_name}'."
            self.audit.log(
                action=f"EXECUTE_TOOL:{norm_name}",
                tool_name=norm_name,
                risk_level=RiskLevel.LOW.value,
                result="BLOCKED",
                error_details=msg,
            )
            return ToolResult.fail(error=msg, message=msg)

        # Step 3: Input schema validation
        try:
            validated_params = tool.input_schema(**arguments)
        except ValidationError as e:
            msg = f"Invalid arguments for tool '{tool.name}': {e}"
            self.audit.log(
                action=f"EXECUTE_TOOL:{tool.name}",
                tool_name=tool.name,
                permission=tool.required_permission.value if tool.required_permission else None,
                risk_level=tool.risk_level.value,
                result="VALIDATION_FAILED",
                error_details=str(e),
            )
            return ToolResult.fail(error=str(e), message="Tool argument schema validation failed.")

        # Step 4 & 5: Check permissions and evaluate policies
        perm_ok = True
        if tool.required_permission:
            perm_ok = self.permissions.is_allowed(tool.required_permission)

        decision: PolicyDecision = self.policy_engine.evaluate(
            tool=tool,
            emergency_stopped=self._emergency_stopped,
            safe_mode=self._safe_mode,
            current_mode=self._operating_mode,
            permission_is_allowed=perm_ok,
        )

        if not decision.allowed:
            self.audit.log(
                action=f"EXECUTE_TOOL:{tool.name}",
                tool_name=tool.name,
                permission=tool.required_permission.value if tool.required_permission else None,
                risk_level=tool.risk_level.value,
                result="POLICY_DENIED",
                error_details=decision.reason,
            )
            return ToolResult.fail(error=decision.reason, message=decision.reason)

        # Step 6: Confirmation check
        confirm_status = "NOT_REQUIRED"
        if tool.requires_confirmation:
            confirm_status = "PENDING"
            confirmed = await self.confirmation.request_confirmation(
                action_name=tool.name,
                risk_level=tool.risk_level,
                details=f"Description: {tool.description}",
            )
            if not confirmed:
                confirm_status = "REJECTED"
                self.audit.log(
                    action=f"EXECUTE_TOOL:{tool.name}",
                    tool_name=tool.name,
                    permission=tool.required_permission.value if tool.required_permission else None,
                    risk_level=tool.risk_level.value,
                    confirmation_status=confirm_status,
                    result="REJECTED_BY_USER",
                )
                return ToolResult.fail(
                    error="Action was not confirmed by user.",
                    message="Operation cancelled.",
                )
            confirm_status = "DOUBLE_CONFIRMED" if tool.requires_double_confirmation else "CONFIRMED"

        # Step 7: Safe execution
        try:
            result = await tool.run(**validated_params.model_dump())
            result_str = "SUCCESS" if result.success else "FAILED"
            self.audit.log(
                action=f"EXECUTE_TOOL:{tool.name}",
                tool_name=tool.name,
                permission=tool.required_permission.value if tool.required_permission else None,
                risk_level=tool.risk_level.value,
                confirmation_status=confirm_status,
                result=result_str,
                error_details=result.error,
                metadata={"message": result.message},
            )
            return result
        except Exception as e:
            logger.exception(f"Unexpected exception during tool execution '{tool.name}': {e}")
            self.audit.log(
                action=f"EXECUTE_TOOL:{tool.name}",
                tool_name=tool.name,
                permission=tool.required_permission.value if tool.required_permission else None,
                risk_level=tool.risk_level.value,
                confirmation_status=confirm_status,
                result="EXCEPTION",
                error_details=str(e),
            )
            return ToolResult.fail(error=str(e), message="Internal tool execution error occurred.")
