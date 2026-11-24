"""JARVIS Safe Memory Tools (Phase 5).

Exposes memory management operations to the central Tool Registry and AI Brain.
All memory tools:
- Require 'memory' permission.
- Are audited through the Security Manager.
- Enforce sensitive data filtering.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from config import PermissionType, RiskLevel
from memory.memory_manager import MemoryManager
from tools.base_tool import BaseTool, EmptyParams, ToolResult

logger = logging.getLogger("jarvis.tools.memory")


class SaveMemoryParams(BaseModel):
    """Parameters for saving a memory."""
    content: str = Field(description="The memory content to store.")
    memory_type: str = Field(
        default="fact",
        description="Category: 'preference', 'personal', 'project', 'instruction', 'fact', 'routine'.",
    )
    importance: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Importance score from 1 (low) to 5 (critical).",
    )


class RecallMemoryParams(BaseModel):
    """Parameters for recalling memories."""
    query: str = Field(description="Search term or topic to recall from memory.")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of memories to return.")


class DeleteMemoryParams(BaseModel):
    """Parameters for deleting a memory."""
    memory_id: str = Field(description="ID of the memory to delete.")


class SaveMemoryTool(BaseTool):
    """Saves a new fact, preference, or instruction to persistent long-term memory."""

    name = "save_memory"
    description = "Saves an approved user fact, preference, project, or instruction into persistent long-term memory."
    input_schema = SaveMemoryParams
    required_permission = PermissionType.MEMORY
    risk_level = RiskLevel.LOW

    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager

    async def run(self, content: str, memory_type: str = "fact", importance: int = 1, **kwargs: Any) -> ToolResult:
        success, msg, item = self.memory.remember(
            content=content,
            memory_type=memory_type,
            importance=importance,
            source="user",
        )
        if success and item:
            return ToolResult.ok(
                message=msg,
                data={"memory_id": item.id, "type": item.memory_type, "content": item.content},
            )
        return ToolResult.fail(error=msg, message=msg)


class RecallMemoryTool(BaseTool):
    """Recalls stored memories matching a search term or topic."""

    name = "recall_memory"
    description = "Searches and recalls stored long-term memories matching a query or topic."
    input_schema = RecallMemoryParams
    required_permission = PermissionType.MEMORY
    risk_level = RiskLevel.LOW

    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager

    async def run(self, query: str, limit: int = 5, **kwargs: Any) -> ToolResult:
        memories = self.memory.search_memories(query=query, limit=limit)
        return ToolResult.ok(
            message=f"Found {len(memories)} matching memory item(s).",
            data={"memories": [m.to_dict() for m in memories], "count": len(memories)},
        )


class ListMemoriesTool(BaseTool):
    """Lists all active stored memories in the system."""

    name = "list_memories"
    description = "Lists all active stored memories categorized by type."
    input_schema = EmptyParams
    required_permission = PermissionType.MEMORY
    risk_level = RiskLevel.LOW

    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager

    async def run(self, **kwargs: Any) -> ToolResult:
        memories = self.memory.list_memories(limit=50)
        return ToolResult.ok(
            message=f"Retrieved {len(memories)} active memory item(s).",
            data={"memories": [m.to_dict() for m in memories], "count": len(memories)},
        )


class DeleteMemoryTool(BaseTool):
    """Permanently deletes a memory record by ID."""

    name = "delete_memory"
    description = "Deletes a specific stored memory by its unique ID."
    input_schema = DeleteMemoryParams
    required_permission = PermissionType.MEMORY
    risk_level = RiskLevel.MEDIUM

    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager

    async def run(self, memory_id: str, **kwargs: Any) -> ToolResult:
        success = self.memory.delete_memory(memory_id.strip())
        if success:
            return ToolResult.ok(
                message=f"Memory '{memory_id}' deleted successfully.",
                data={"memory_id": memory_id},
            )
        return ToolResult.fail(
            error=f"Memory '{memory_id}' not found.",
            message=f"Could not find memory with ID '{memory_id}'.",
        )
