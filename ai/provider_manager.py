"""JARVIS Centralized AI Provider Manager.

Coordinates dual AI providers:
- Primary: Google Gemini API (gemini-3.8-flash / configured GEMINI_MODEL)
- Backup: OpenRouter API (openrouter/auto / configured OPENROUTER_MODEL)

STRICT ZERO-LEAKAGE & RESILIENCE RULES:
- Zero-Trust Permission Check: Gated by PermissionManager (CLOUD_AI).
- Deterministic Fallback: Tries Primary first; falls back to Backup on recoverable errors.
- Prevents infinite retries: Exactly one fallback attempt per request.
- Prevents duplicate responses: Awaits only the chosen provider result.
- Preserves full conversational and memory context on fallback.
- Never prints or logs raw API keys or credentials.
- Broadcasts fallback events to listeners (e.g., UI/WebSocket).
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Callable, Dict, List, Optional

from ai.gemini_provider import GeminiProvider
from ai.openrouter_provider import OpenRouterProvider
from ai.provider import AIResult, BaseAIProvider
from config import PermissionType, Settings
from security.permission_manager import PermissionManager
from tools.registry import ToolRegistry

logger = logging.getLogger("jarvis.ai.provider_manager")


class AIProviderManager(BaseAIProvider):
    """Centralized manager coordinating primary (Gemini) and backup (OpenRouter) AI providers."""

    name = "dual_provider_manager"

    def __init__(
        self,
        settings: Settings,
        registry: ToolRegistry,
        permissions: PermissionManager,
        gemini_provider: Optional[BaseAIProvider] = None,
        openrouter_provider: Optional[BaseAIProvider] = None,
    ):
        self.settings = settings
        self.registry = registry
        self.permissions = permissions

        # Child providers
        self.gemini = gemini_provider or GeminiProvider(settings, registry, permissions)
        self.openrouter = openrouter_provider or OpenRouterProvider(settings, registry, permissions)

        # Provider selection & fallback tracking
        primary_pref = (getattr(settings, "ai_primary_provider", None) or "gemini").lower()
        self.primary_name = "openrouter" if primary_pref == "openrouter" else "gemini"
        self.backup_name = "gemini" if self.primary_name == "openrouter" else "openrouter"

        self.active_provider_name: str = self.primary_name
        self.fallback_active: bool = False
        self.last_fallback_reason: Optional[str] = None
        self.last_fallback_timestamp: Optional[float] = None
        self._fallback_listeners: List[Callable[[Dict[str, Any]], None]] = []

    @property
    def primary(self) -> BaseAIProvider:
        return self.openrouter if self.primary_name == "openrouter" else self.gemini

    @property
    def backup(self) -> BaseAIProvider:
        return self.gemini if self.primary_name == "openrouter" else self.openrouter

    def get_active_provider(self) -> BaseAIProvider:
        if self.active_provider_name == self.backup.name:
            return self.backup
        return self.primary

    def is_available(self) -> bool:
        """Available if at least one cloud provider is configured and allowed."""
        cloud_permitted = self.permissions.is_allowed(PermissionType.CLOUD_AI)
        if not cloud_permitted:
            return False
        return self.primary.is_available() or self.backup.is_available()

    def add_fallback_listener(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback invoked when automatic provider fallback occurs."""
        self._fallback_listeners.append(callback)

    def _notify_fallback(self, from_provider: str, to_provider: str, reason: str) -> None:
        """Notify registered listeners and update state on provider fallback."""
        self.fallback_active = True
        self.active_provider_name = to_provider
        self.last_fallback_reason = reason
        self.last_fallback_timestamp = time.time()

        payload = {
            "from_provider": from_provider,
            "to_provider": to_provider,
            "reason": reason,
            "timestamp": self.last_fallback_timestamp,
        }

        for listener in self._fallback_listeners:
            try:
                listener(payload)
            except Exception as e:
                logger.warning(f"Error in fallback listener: {e}")

    def _sanitize(self, text: Optional[str]) -> str:
        """Scrub API key strings and authorization headers from error messages."""
        if not text:
            return ""
        scrubbed = text
        for key in (self.settings.gemini_api_key, self.settings.openrouter_api_key):
            if key and key.strip():
                scrubbed = scrubbed.replace(key.strip(), "[REDACTED_KEY]")
        scrubbed = re.sub(r'AIzaSy[A-Za-z0-9_-]{33}', '[REDACTED_GEMINI_KEY]', scrubbed)
        scrubbed = re.sub(r'sk-or-v1-[A-Za-z0-9_-]{32,}', '[REDACTED_OPENROUTER_KEY]', scrubbed)
        return scrubbed

    def is_recoverable_failure(self, error_msg: Optional[str]) -> bool:
        """Identify transient/recoverable provider failures that warrant automatic fallback."""
        if not error_msg:
            return False
        lower = error_msg.lower()

        # Rate limits, timeouts, service outages, network errors, model deprecation/404
        recoverable_indicators = (
            "404", "not found", "not_found", "no longer available",
            "429", "rate limit", "resource_exhausted", "quota",
            "500", "502", "503", "504", "unavailable", "internal error", "service error",
            "timeout", "timed out", "deadline", "connection", "network error",
            "not configured", "not available", "unreachable",
        )
        return any(ind in lower for ind in recoverable_indicators)

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AIResult:
        """Route generation request to Primary (Gemini) with automatic fallback to Backup (OpenRouter)."""
        primary = self.primary
        backup = self.backup

        # 1. Zero-Trust Permission Check: Cloud AI must be allowed
        if not self.permissions.is_allowed(PermissionType.CLOUD_AI):
            err_msg = "Cloud AI permission is BLOCKED. Run 'allow cloud_ai' first to enable online reasoning."
            logger.warning(err_msg)
            return AIResult.fail(err_msg, provider=self.name)

        # 2. Check if Primary is available
        if not primary.is_available():
            if backup.is_available():
                reason = f"Primary provider '{primary.name}' is unavailable/not configured"
                logger.info(f"{reason}. Using backup provider '{backup.name}'.")
                self._notify_fallback(primary.name, backup.name, reason)
                return await backup.generate_response(prompt, system_prompt, tools)
            else:
                return AIResult.fail(
                    "No AI provider available. Neither Gemini nor OpenRouter is configured and permitted.",
                    provider=self.name,
                )

        # 3. Attempt generation with Primary provider
        self.active_provider_name = primary.name
        primary_result: Optional[AIResult] = None
        try:
            primary_result = await primary.generate_response(prompt, system_prompt, tools)
        except Exception as exc:
            sanitized_err = self._sanitize(str(exc))
            logger.error(f"Primary provider '{primary.name}' raised unexpected exception: {sanitized_err}")
            primary_result = AIResult.fail(sanitized_err, provider=primary.name)

        # 4. Check for success
        if primary_result and not primary_result.error:
            self.fallback_active = False
            self.active_provider_name = primary.name
            return primary_result

        # 5. Handle Primary Failure -> Automatic Fallback
        err_msg = primary_result.error if primary_result else "Unknown primary provider failure"
        sanitized_primary_err = self._sanitize(err_msg)

        if self.is_recoverable_failure(sanitized_primary_err) and backup.is_available():
            reason = f"Primary ({primary.name}) error: {sanitized_primary_err}"
            logger.warning(
                f"Recoverable failure in primary provider '{primary.name}': {sanitized_primary_err}. "
                f"Initiating automatic fallback to backup provider '{backup.name}'."
            )
            self._notify_fallback(primary.name, backup.name, reason)

            # Single fallback attempt: avoid infinite retry loops
            backup_result: Optional[AIResult] = None
            try:
                backup_result = await backup.generate_response(prompt, system_prompt, tools)
            except Exception as exc:
                sanitized_backup_exc = self._sanitize(str(exc))
                logger.error(f"Backup provider '{backup.name}' raised unexpected exception: {sanitized_backup_exc}")
                backup_result = AIResult.fail(sanitized_backup_exc, provider=backup.name)

            if backup_result and not backup_result.error:
                logger.info(f"Backup provider '{backup.name}' responded successfully after fallback.")
                return backup_result
            else:
                # Both failed!
                sanitized_backup_err = self._sanitize(backup_result.error if backup_result else "Unknown error")
                combined_err = (
                    f"Both AI providers failed. "
                    f"Primary ({primary.name}): {sanitized_primary_err}; "
                    f"Backup ({backup.name}): {sanitized_backup_err}"
                )
                logger.error(combined_err)
                return AIResult.fail(combined_err, provider=self.name)

        # If error was not recoverable or backup is unavailable, return primary result
        return primary_result

    def get_model_info(self) -> Dict[str, Any]:
        """Return diagnostic metadata about dual provider configuration and fallback state."""
        active = self.get_active_provider()
        return {
            "provider": self.name,
            "active_provider": self.active_provider_name,
            "primary_provider": self.primary.name,
            "backup_provider": self.backup.name,
            "configured_model": getattr(active, "model_name", "unknown"),
            "fallback_active": self.fallback_active,
            "last_fallback_reason": self.last_fallback_reason,
            "last_fallback_timestamp": self.last_fallback_timestamp,
            "primary_info": self.primary.get_model_info(),
            "backup_info": self.backup.get_model_info(),
            "provider_available": self.is_available(),
        }
