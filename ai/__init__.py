"""JARVIS AI Brain Subsystem (Phase 4).

Exports AI providers, structured parser, and result models.
"""

from ai.provider import AIResult, BaseAIProvider, ToolCallRequest
from ai.local_provider import LIGHTWEIGHT_MODEL_RECOMMENDATIONS, LocalAIProvider
from ai.openrouter_provider import OpenRouterProvider
from ai.gemini_provider import GeminiProvider
from ai.provider_manager import AIProviderManager
from ai.tool_call_parser import ToolCallParser

__all__ = [
    "BaseAIProvider",
    "AIResult",
    "ToolCallRequest",
    "LocalAIProvider",
    "OpenRouterProvider",
    "GeminiProvider",
    "AIProviderManager",
    "ToolCallParser",
    "LIGHTWEIGHT_MODEL_RECOMMENDATIONS",
]
