"""JARVIS Configuration System.

Centralized, type-safe settings loaded from environment variables and .env file.
Adheres strictly to the Privacy-First and Security-First principles:
- Default operating mode: OFFLINE
- Default safe mode: ON
- Permissions defaulted to BLOCKED
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load .env if present
load_dotenv()


class OperatingMode(str, Enum):
    """JARVIS operating modes controlling network and external capabilities."""
    OFFLINE = "offline"   # Strictly local AI, tools, and storage. No network calls.
    HYBRID = "hybrid"     # Local-first; network allowed ONLY for explicitly permitted tools.
    ONLINE = "online"     # Cloud AI and online capabilities enabled when permitted.


class Environment(str, Enum):
    """Runtime environment."""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class RiskLevel(str, Enum):
    """Risk classification for tool actions."""
    LOW = "LOW"             # Read-only or completely benign operations.
    MEDIUM = "MEDIUM"       # Non-destructive state alterations.
    HIGH = "HIGH"           # Potentially disruptive; requires user confirmation.
    CRITICAL = "CRITICAL"   # Destructive/system-level; requires double confirmation.


class PermissionType(str, Enum):
    """Standard JARVIS permissions. All start BLOCKED by default."""
    MICROPHONE = "microphone"
    INTERNET = "internet"
    FILES = "files"
    SCREEN = "screen"
    PC_CONTROL = "pc_control"
    AUTOMATION = "automation"
    CLOUD_AI = "cloud_ai"
    WEB_ACCESS = "web_access"
    MEMORY = "memory"


class Settings(BaseModel):
    """Core settings schema for JARVIS."""
    app_name: str = "JARVIS"
    version: str = "1.0.0-phase5"
    
    # Environment & Operating Mode
    jarvis_env: Environment = Field(
        default_factory=lambda: Environment(os.getenv("JARVIS_ENV", "development").lower())
    )
    jarvis_mode: OperatingMode = Field(
        default_factory=lambda: OperatingMode(os.getenv("JARVIS_MODE", "offline").lower())
    )
    safe_mode: bool = Field(
        default_factory=lambda: os.getenv("SAFE_MODE", "true").lower() in ("true", "1", "yes")
    )
    require_double_confirmation_for_critical: bool = Field(
        default_factory=lambda: os.getenv("REQUIRE_DOUBLE_CONFIRMATION_FOR_CRITICAL", "true").lower() in ("true", "1", "yes")
    )

    # AI Brain Configuration (Phase 4)
    ai_enabled: bool = Field(
        default_factory=lambda: os.getenv("AI_ENABLED", "true").lower() in ("true", "1", "yes")
    )
    ai_mode: str = Field(
        default_factory=lambda: os.getenv("AI_MODE", "local").lower()
    )
    ai_provider: str = Field(
        default_factory=lambda: os.getenv("AI_PROVIDER", "local").lower()
    )
    ai_temperature: float = Field(
        default_factory=lambda: float(os.getenv("AI_TEMPERATURE", "0.2"))
    )
    ai_max_tokens: int = Field(
        default_factory=lambda: int(os.getenv("AI_MAX_TOKENS", "500"))
    )
    local_model_endpoint: str = Field(
        default_factory=lambda: os.getenv("LOCAL_MODEL_ENDPOINT", "http://127.0.0.1:11434")
    )
    local_model_name: str = Field(
        default_factory=lambda: os.getenv("LOCAL_MODEL_NAME", "qwen2.5:1.5b")
    )
    ai_primary_provider: str = Field(
        default_factory=lambda: os.getenv("AI_PRIMARY_PROVIDER", "gemini").lower()
    )
    gemini_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY") or None
    )
    gemini_model: str = Field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    )
    openrouter_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY") or None
    )
    openrouter_model: str = Field(
        default_factory=lambda: os.getenv("OPENROUTER_MODEL", "openrouter/auto")
    )

    # Voice Configuration (Phase 3)
    voice_enabled: bool = Field(
        default_factory=lambda: os.getenv("VOICE_ENABLED", "true").lower() in ("true", "1", "yes")
    )
    wake_phrase: str = Field(default_factory=lambda: os.getenv("WAKE_PHRASE", "Jarvis"))
    inactivity_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("INACTIVITY_TIMEOUT_SECONDS", "60.0"))
    )
    wake_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("WAKE_TIMEOUT_SECONDS", "5.0"))
    )
    command_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("COMMAND_TIMEOUT_SECONDS", "8.0"))
    )
    tts_enabled: bool = Field(
        default_factory=lambda: os.getenv("TTS_ENABLED", "true").lower() in ("true", "1", "yes")
    )
    tts_engine: str = Field(default_factory=lambda: os.getenv("TTS_ENGINE", "pyttsx3"))
    tts_voice_rate: int = Field(default_factory=lambda: int(os.getenv("TTS_VOICE_RATE", "180")))
    tts_voice_volume: float = Field(default_factory=lambda: float(os.getenv("TTS_VOICE_VOLUME", "1.0")))
    stt_provider: str = Field(default_factory=lambda: os.getenv("STT_PROVIDER", "local"))
    tts_provider: str = Field(default_factory=lambda: os.getenv("TTS_PROVIDER", "local"))

    # Memory & Context Configuration (Phase 5)
    memory_enabled: bool = Field(
        default_factory=lambda: os.getenv("MEMORY_ENABLED", "true").lower() in ("true", "1", "yes")
    )
    conversation_history_enabled: bool = Field(
        default_factory=lambda: os.getenv("CONVERSATION_HISTORY_ENABLED", "true").lower() in ("true", "1", "yes")
    )
    max_context_messages: int = Field(
        default_factory=lambda: int(os.getenv("MAX_CONTEXT_MESSAGES", "10"))
    )
    max_relevant_memories: int = Field(
        default_factory=lambda: int(os.getenv("MAX_RELEVANT_MEMORIES", "5"))
    )

    # Storage Paths
    data_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("DATA_DIR", "data")).resolve()
    )
    db_path: Path = Field(
        default_factory=lambda: Path(os.getenv("DB_PATH", "data/jarvis.db")).resolve()
    )
    log_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("LOG_DIR", "data/logs")).resolve()
    )
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    def ensure_directories(self) -> None:
        """Create necessary directories if they do not exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def is_offline(self) -> bool:
        return self.jarvis_mode == OperatingMode.OFFLINE

    @property
    def is_online(self) -> bool:
        return self.jarvis_mode == OperatingMode.ONLINE


# Global singleton settings instance
settings = Settings()
