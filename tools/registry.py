"""JARVIS Central Tool Registry.

Manages all registered tools, their schemas, permissions, and risk metadata.
Ensures no duplicate or improperly defined tools are registered.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional
from tools.base_tool import BaseTool

logger = logging.getLogger("jarvis.tools.registry")


class ToolRegistry:
    """Central catalog of approved system tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._aliases: Dict[str, str] = {
            "open_app": "open_application",
            "list_approved_apps": "list_approved_applications",
            "list_apps": "list_approved_applications",
            "search": "search_files",
            "find_files": "search_files",
            "remember": "save_memory",
            "recall": "recall_memory",
            "search_memory": "recall_memory",
            "list_memory": "list_memories",
            "forget": "delete_memory",
        }

    def register(self, tool: BaseTool) -> None:
        """Register a new approved tool."""
        if not tool.name:
            raise ValueError("Tool name must not be empty.")
        norm_name = tool.name.strip().lower()
        if norm_name in self._tools:
            logger.warning(f"Tool '{norm_name}' already registered; overwriting.")
        self._tools[norm_name] = tool
        logger.info(f"Registered tool: '{norm_name}' (Permission: {tool.required_permission}, Risk: {tool.risk_level.value})")

    def unregister(self, name: str) -> bool:
        """Remove a tool from registry."""
        norm_name = name.strip().lower()
        canonical = self._aliases.get(norm_name, norm_name)
        if canonical in self._tools:
            del self._tools[canonical]
            logger.info(f"Unregistered tool: '{canonical}'")
            return True
        return False

    def get(self, name: str) -> Optional[BaseTool]:
        """Look up tool by canonical name or alias."""
        norm_name = name.strip().lower()
        canonical = self._aliases.get(norm_name, norm_name)
        return self._tools.get(canonical)

    def has(self, name: str) -> bool:
        """Check if a tool exists by canonical name or alias."""
        norm_name = name.strip().lower()
        canonical = self._aliases.get(norm_name, norm_name)
        return canonical in self._tools

    def list_tools(self) -> List[BaseTool]:
        """Return list of all registered tools."""
        return list(self._tools.values())

    def get_metadata_list(self) -> List[Dict[str, str]]:
        """Return a formatted list of tool metadata for display or inspection."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "permission": tool.required_permission.value if tool.required_permission else "NONE",
                "risk_level": tool.risk_level.value,
                "confirmation": "DOUBLE" if tool.requires_double_confirmation else ("SINGLE" if tool.requires_confirmation else "NO"),
            }
            for tool in self._tools.values()
        ]

    def get_ai_schemas(self) -> List[Dict]:
        """Generate JSON schemas for AI function calling."""
        return [tool.get_schema() for tool in self._tools.values()]
