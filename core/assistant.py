"""JARVIS Assistant Core.

The primary coordinator for all JARVIS subsystems:
- Settings & environment
- Database & memory
- Permission & privacy control
- Security & confirmation enforcement
- Tool execution
- Structured audit logging
- Status & diagnostic reporting
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from config import OperatingMode, PermissionType, RiskLevel, Settings, settings
from memory.database import DatabaseManager
from security.audit_logger import AuditLogger, close_logging, setup_logging
from security.confirmation_manager import ConfirmationManager
from security.permission_manager import PermissionManager
from security.security_manager import SecurityManager
from tools.base_tool import ToolResult
from tools.registry import ToolRegistry
from tools import (
    CopyFileTool,
    CreateFolderTool,
    CreateTextFileTool,
    EchoTool,
    ListApprovedAppsTool,
    MoveFileTool,
    OpenAppTool,
    OpenFolderTool,
    RenameFileTool,
    SearchFilesTool,
    SystemStatusTool,
    SaveMemoryTool,
    RecallMemoryTool,
    ListMemoriesTool,
    DeleteMemoryTool,
)
from memory.conversation_store import ConversationStore
from memory.memory_manager import MemoryManager
from core.context_manager import ContextManager
from core.brain import AIBrain
from voice import VoiceManager, VoiceState

logger = logging.getLogger("jarvis.core.assistant")


class JarvisAssistant:
    """Core JARVIS assistant orchestrator."""

    def __init__(self, custom_settings: Optional[Settings] = None):
        self.settings = custom_settings or settings
        self.settings.ensure_directories()

        # 1. Setup segregated logging
        setup_logging(self.settings.log_dir, self.settings.log_level)
        logger.info(f"Starting {self.settings.app_name} v{self.settings.version} in {self.settings.jarvis_mode.value.upper()} mode...")

        # 2. Initialize Database & Audit Logger
        self.db = DatabaseManager(self.settings.db_path)
        self.audit = AuditLogger(self.settings.log_dir, self.db)

        # 3. Privacy & Permission Manager (Default: Zero Trust / All Blocked)
        self.permissions = PermissionManager(self.db, self.audit)

        # 4. Long-Term Memory & Context Subsystems (Phase 5)
        self.conversations = ConversationStore(self.db)
        self.memory = MemoryManager(self.db, self.permissions, self.audit)
        self.context = ContextManager(self.settings, self.conversations, self.memory)

        # 5. Confirmation Manager (Interactive approvals)
        self.confirmation = ConfirmationManager()

        # 6. Tool Registry & Register initial tools
        self.registry = ToolRegistry()
        self._register_default_tools()

        # 7. Central Security Manager
        self.security = SecurityManager(
            settings=self.settings,
            permission_manager=self.permissions,
            confirmation_manager=self.confirmation,
            audit_logger=self.audit,
            tool_registry=self.registry,
        )

        # 8. AI Brain (Phase 4 & 5 Context-Aware)
        self.brain = AIBrain(
            settings=self.settings,
            registry=self.registry,
            permissions=self.permissions,
            security=self.security,
            context_manager=self.context,
            memory_manager=self.memory,
        )

        # 9. Voice Interaction Manager (Phase 3)
        self.voice = VoiceManager(
            settings=self.settings,
            permission_manager=self.permissions,
            command_handler=self.dispatch_command,
        )
        self._command_router = None

        logger.info("JARVIS Core Assistant initialized successfully.")

    def _register_default_tools(self) -> None:
        """Register approved system tools."""
        # System diagnostics
        self.registry.register(SystemStatusTool())
        self.registry.register(EchoTool())

        # Application launcher (Phase 2)
        self.registry.register(OpenAppTool())
        self.registry.register(ListApprovedAppsTool())

        # Folder launcher & Safe File Management (Phase 2)
        self.registry.register(OpenFolderTool())
        self.registry.register(SearchFilesTool())
        self.registry.register(CreateFolderTool())
        self.registry.register(CreateTextFileTool())
        self.registry.register(RenameFileTool())
        self.registry.register(CopyFileTool())
        self.registry.register(MoveFileTool())

        # Long-Term Memory Tools (Phase 5)
        self.registry.register(SaveMemoryTool(self.memory))
        self.registry.register(RecallMemoryTool(self.memory))
        self.registry.register(ListMemoriesTool(self.memory))
        self.registry.register(DeleteMemoryTool(self.memory))

    def get_status_report(self) -> Dict[str, Any]:
        """Generate a complete diagnostic status report of all subsystems."""
        mic_allowed = self.permissions.is_allowed(PermissionType.MICROPHONE)
        net_allowed = self.permissions.is_allowed(PermissionType.INTERNET)
        db_ok = True
        try:
            with self.db.get_connection() as conn:
                conn.execute("SELECT 1")
        except Exception:
            db_ok = False

        voice_state_str = self.voice.state.value
        if not mic_allowed:
            voice_subsystem_str = f"OFF (Microphone blocked | State: {voice_state_str})"
        else:
            voice_subsystem_str = f"ACTIVE (State: {voice_state_str} | Wake: \"{self.settings.wake_phrase}\")"

        cloud_ai_allowed = self.permissions.is_allowed(PermissionType.CLOUD_AI)
        mem_allowed = self.permissions.is_allowed(PermissionType.MEMORY)
        stored_memories_count = len(self.memory.list_memories()) if mem_allowed else 0
        active_session_id = self.context.get_current_session_id()
        mem_info = self.brain.get_resource_usage()
        model_info = self.brain.provider.get_model_info()

        active_provider = model_info.get("active_provider", getattr(self.brain.provider, "name", "unknown"))
        configured_model = model_info.get("configured_model", "N/A")
        fallback_active = model_info.get("fallback_active", False)
        fallback_suffix = " [Fallback: OpenRouter]" if fallback_active and active_provider == "openrouter" else ""
        ai_provider_display = f"{active_provider.capitalize()} ({configured_model}){fallback_suffix}"

        return {
            "assistant_name": self.settings.app_name,
            "version": self.settings.version,
            "operating_mode": self.security.operating_mode.value.upper(),
            "safe_mode": "ENABLED" if self.security.safe_mode else "DISABLED",
            "emergency_stopped": self.security.emergency_stopped,
            "voice_subsystem": voice_subsystem_str,
            "voice_state": voice_state_str,
            "is_muted": getattr(self.voice, "is_muted", False),
            "seconds_until_sleep": getattr(self.voice, "seconds_until_sleep", 0.0),
            "inactivity_timeout_seconds": getattr(self.voice, "inactivity_timeout_seconds", 60.0),
            "wake_phrase": self.settings.wake_phrase,
            "microphone_permission": "ALLOWED" if mic_allowed else "BLOCKED",
            "internet_permission": "ALLOWED" if net_allowed else "BLOCKED",
            "cloud_ai_permission": "ALLOWED" if cloud_ai_allowed else "BLOCKED",
            "memory_permission": "ALLOWED" if mem_allowed else "BLOCKED",
            "memory_subsystem": f"ACTIVE ({stored_memories_count} items stored)" if mem_allowed else "OFF (Memory blocked)",
            "stored_memories_count": stored_memories_count,
            "session_id": active_session_id,
            "ai_mode": self.settings.ai_mode.upper(),
            "ai_provider": ai_provider_display,
            "ai_provider_available": "ONLINE" if self.brain.is_provider_available() else "NOT CONFIGURED",
            "ai_active_provider": active_provider,
            "ai_primary_provider": model_info.get("primary_provider", "gemini"),
            "ai_backup_provider": model_info.get("backup_provider", "openrouter"),
            "ai_fallback_active": fallback_active,
            "ai_fallback_reason": model_info.get("last_fallback_reason"),
            "gemini_status": model_info.get("primary_info", {}).get("api_key_status", "N/A") if "primary_info" in model_info else "N/A",
            "openrouter_status": model_info.get("backup_info", {}).get("api_key_status", "N/A") if "backup_info" in model_info else "N/A",
            "memory_usage": f"{mem_info['process_rss_mb']} MB (System: {mem_info['system_available_ram_gb']} GB free)",
            "database_status": "ONLINE (WAL Mode)" if db_ok else "ERROR",
            "database_path": str(self.settings.db_path),
            "registered_tools_count": len(self.registry.list_tools()),
            "automation_subsystem": "STANDBY (Phase 8)",
        }

    def set_router(self, router: Any) -> None:
        """Attach command router for processing recognized voice commands."""
        self._command_router = router

    async def dispatch_command(self, cmd: str) -> str:
        """Route recognized voice command through the existing command router."""
        if self._command_router:
            return await self._command_router.handle_command(cmd)
        return f"Command received: {cmd}"

    async def execute_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> ToolResult:
        """Execute tool through the central security manager."""
        return await self.security.execute_tool(tool_name, arguments)

    def shutdown(self) -> None:
        """Cleanly shutdown subsystems and release file handles."""
        logger.info("Shutting down JARVIS subsystems...")
        if hasattr(self, "voice"):
            self.voice.stop_listening()
            if hasattr(self.voice, "tts") and hasattr(self.voice.tts, "shutdown"):
                try:
                    self.voice.tts.shutdown()
                except Exception:
                    pass
        close_logging()
