"""JARVIS Base Tool Definition.

Every tool in the system inherits from BaseTool and strictly specifies:
- Unique name
- Human-readable description
- Strongly-typed Pydantic input schema
- Required permission (PermissionType or None)
- Risk level (LOW, MEDIUM, HIGH, CRITICAL)
- Execution handler returning ToolResult

Tools NEVER interact directly with arbitrary shell commands.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field
from config import PermissionType, RiskLevel


class EmptyParams(BaseModel):
    """Empty parameters schema for tools requiring no arguments."""
    pass


class ToolResult(BaseModel):
    """Standardized output structure for all tool executions."""
    success: bool
    message: str = ""
    data: Any = None
    error: Optional[str] = None

    @classmethod
    def ok(cls, message: str = "Success", data: Any = None) -> ToolResult:
        return cls(success=True, message=message, data=data)

    @classmethod
    def fail(cls, error: str, message: str = "Failed", data: Any = None) -> ToolResult:
        return cls(success=False, message=message, error=error, data=data)


class BaseTool(ABC):
    """Abstract Base Class for all JARVIS tools."""

    name: str
    description: str
    input_schema: Type[BaseModel] = EmptyParams
    output_schema: Optional[Type[BaseModel]] = None
    required_permission: Optional[PermissionType] = None
    risk_level: RiskLevel = RiskLevel.LOW

    @property
    def requires_confirmation(self) -> bool:
        """Indicates whether this tool requires at least single user confirmation."""
        return self.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    @property
    def requires_double_confirmation(self) -> bool:
        """Indicates whether this tool requires double user confirmation."""
        return self.risk_level == RiskLevel.CRITICAL

    @abstractmethod
    async def run(self, **kwargs: Any) -> ToolResult:
        """Execute the tool logic safely."""
        pass

    def get_schema(self) -> Dict[str, Any]:
        """Generate OpenAI/OpenRouter compatible JSON Schema for AI function calling."""
        schema_dict = self.input_schema.model_json_schema()
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": schema_dict.get("properties", {}),
                    "required": schema_dict.get("required", []),
                },
                "metadata": {
                    "required_permission": self.required_permission.value if self.required_permission else None,
                    "risk_level": self.risk_level.value,
                }
            }
        }
