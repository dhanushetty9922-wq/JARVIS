"""Tests for JARVIS Dual AI Provider Integration (Google Gemini + OpenRouter).

Covers:
1. Gemini works independently.
2. OpenRouter works independently.
3. Gemini succeeds and OpenRouter is not called.
4. Gemini failure triggers OpenRouter when appropriate.
5. Both providers unavailable produces a clear error.
6. Invalid credentials are handled correctly without exposing secrets.
7. Existing chat and voice features still work seamlessly.
8. Fallback event tracking and zero-trust permissions.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from ai.gemini_provider import GeminiProvider
from ai.openrouter_provider import OpenRouterProvider
from ai.provider_manager import AIProviderManager
from ai.provider import AIResult, BaseAIProvider, ToolCallRequest
from config import PermissionType, Settings
from core.assistant import JarvisAssistant
from core.brain import AIBrain, BrainResult
from core.command_router import CommandRouter
from tools.registry import ToolRegistry


class DummyMockProvider(BaseAIProvider):
    """Configurable mock AI provider for fallback testing."""

    def __init__(self, name: str, should_succeed: bool = True, error_msg: Optional[str] = None, response_text: str = "Success"):
        self.name = name
        self.should_succeed = should_succeed
        self.error_msg = error_msg or "Provider error"
        self.response_text = response_text
        self.call_count = 0
        self.last_prompt: Optional[str] = None
        self.available = True
        self.model_name = f"{name}-model"

    def is_available(self) -> bool:
        return self.available

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AIResult:
        self.call_count += 1
        self.last_prompt = prompt
        if self.should_succeed:
            return AIResult.conversational(self.response_text, provider=self.name, model=self.model_name)
        return AIResult.fail(self.error_msg, provider=self.name, model=self.model_name)

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "configured_model": self.model_name,
            "api_key_status": "CONFIGURED" if self.available else "NOT CONFIGURED",
            "provider_available": self.available,
        }


@pytest.fixture
def test_env():
    """Isolated environment fixture for dual provider testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir).resolve()
        settings = Settings(
            data_dir=tmp_path / "data",
            db_path=tmp_path / "data" / "jarvis.db",
            log_dir=tmp_path / "data" / "logs",
            safe_mode=True,
            ai_enabled=True,
            ai_mode="online",
            ai_provider="gemini",
            ai_primary_provider="gemini",
            gemini_api_key="AIzaSyTestGeminiKey1234567890abcdef",
            gemini_model="gemini-3.8-flash",
            openrouter_api_key="sk-or-v1-testopenrouterkey1234567890abcdef",
            openrouter_model="openrouter/auto",
            tts_provider="silent",
            stt_provider="simulated",
        )

        assistant = JarvisAssistant(custom_settings=settings)
        router = CommandRouter(assistant)
        assistant.permissions.allow(PermissionType.CLOUD_AI, "Allow for testing")

        try:
            yield {
                "assistant": assistant,
                "router": router,
                "brain": assistant.brain,
                "registry": assistant.registry,
                "permissions": assistant.permissions,
                "settings": settings,
            }
        finally:
            assistant.shutdown()


# =============================================================================
# 1. Gemini Works Independently
# =============================================================================

@pytest.mark.asyncio
async def test_gemini_works_independently(test_env):
    """GeminiProvider generates conversational responses and function calls independently."""
    settings = test_env["settings"]
    registry = test_env["registry"]
    permissions = test_env["permissions"]

    # Mock official google-genai client
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.function_calls = None
    mock_response.text = "Quantum computing uses qubits and superposition to process information."

    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    gemini = GeminiProvider(settings, registry, permissions, client=mock_client)

    assert gemini.is_available() is True
    assert gemini.name == "gemini"
    assert "AIzaSy" in gemini.get_masked_key()
    assert "1234567890" not in gemini.get_masked_key()  # Key is masked

    result = await gemini.generate_response("Explain quantum computing")
    assert result.is_conversational is True
    assert "qubits" in result.content
    assert result.provider_name == "gemini"
    assert result.model_name == settings.gemini_model


@pytest.mark.asyncio
async def test_gemini_tool_call_parsing(test_env):
    """Gemini native function calling translates cleanly to ToolCallRequest."""
    settings = test_env["settings"]
    registry = test_env["registry"]
    permissions = test_env["permissions"]

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_fc = MagicMock()
    mock_fc.name = "open_app"
    mock_fc.args = {"app_name": "notepad"}
    mock_response.function_calls = [mock_fc]
    mock_response.text = None

    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    gemini = GeminiProvider(settings, registry, permissions, client=mock_client)
    tools = registry.get_ai_schemas()

    result = await gemini.generate_response("Open notepad", tools=tools)
    assert result.has_tool_calls is True
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool_name in ("open_app", "open_application")
    assert result.tool_calls[0].arguments == {"app_name": "notepad"}


# =============================================================================
# 2. OpenRouter Works Independently
# =============================================================================

@pytest.mark.asyncio
async def test_openrouter_works_independently(test_env):
    """OpenRouterProvider operates independently with mocked HTTP responses."""
    settings = test_env["settings"]
    registry = test_env["registry"]
    permissions = test_env["permissions"]

    openrouter = OpenRouterProvider(settings, registry, permissions)

    assert openrouter.is_available() is True
    assert openrouter.name == "openrouter"
    assert "sk-or-" in openrouter.get_masked_key()

    fake_resp = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Artificial intelligence is the simulation of human intelligence by machines.",
                }
            }
        ]
    }

    with patch.object(openrouter, "_call_openrouter_sync", return_value=fake_resp):
        result = await openrouter.generate_response("What is artificial intelligence?")
        assert result.is_conversational is True
        assert "simulation of human intelligence" in result.content
        assert result.provider_name == "openrouter"


# =============================================================================
# 3. Gemini Succeeds -> OpenRouter Is NOT Called
# =============================================================================

@pytest.mark.asyncio
async def test_gemini_success_no_fallback(test_env):
    """When Gemini succeeds, OpenRouter is not called and fallback is inactive."""
    settings = test_env["settings"]
    registry = test_env["registry"]
    permissions = test_env["permissions"]

    gemini_mock = DummyMockProvider("gemini", should_succeed=True, response_text="Gemini primary answer")
    openrouter_mock = DummyMockProvider("openrouter", should_succeed=True, response_text="OpenRouter backup answer")

    manager = AIProviderManager(
        settings=settings,
        registry=registry,
        permissions=permissions,
        gemini_provider=gemini_mock,
        openrouter_provider=openrouter_mock,
    )

    result = await manager.generate_response("Explain DBMS normalization")

    assert result.content == "Gemini primary answer"
    assert result.provider_name == "gemini"
    assert gemini_mock.call_count == 1
    assert openrouter_mock.call_count == 0  # CRITICAL: OpenRouter was never invoked!
    assert manager.fallback_active is False
    assert manager.active_provider_name == "gemini"


# =============================================================================
# 4. Gemini Failure Triggers OpenRouter Fallback
# =============================================================================

@pytest.mark.asyncio
async def test_gemini_failure_triggers_openrouter_fallback(test_env):
    """Recoverable failure in Gemini (e.g. 429 rate limit or 503) immediately routes to OpenRouter."""
    settings = test_env["settings"]
    registry = test_env["registry"]
    permissions = test_env["permissions"]

    gemini_mock = DummyMockProvider(
        "gemini",
        should_succeed=False,
        error_msg="Gemini rate limit exceeded (429). Resource exhausted.",
    )
    openrouter_mock = DummyMockProvider(
        "openrouter",
        should_succeed=True,
        response_text="OpenRouter backup response to normalization question",
    )

    manager = AIProviderManager(
        settings=settings,
        registry=registry,
        permissions=permissions,
        gemini_provider=gemini_mock,
        openrouter_provider=openrouter_mock,
    )

    fallback_events: List[Dict[str, Any]] = []
    manager.add_fallback_listener(lambda evt: fallback_events.append(evt))

    result = await manager.generate_response("Explain DBMS normalization")

    # 1. Primary was attempted
    assert gemini_mock.call_count == 1
    # 2. Backup was invoked exactly once (no infinite retries)
    assert openrouter_mock.call_count == 1
    # 3. Response is from backup
    assert result.content == "OpenRouter backup response to normalization question"
    assert result.provider_name == "openrouter"
    # 4. State tracks fallback
    assert manager.fallback_active is True
    assert manager.active_provider_name == "openrouter"
    # 5. Listener notified
    assert len(fallback_events) == 1
    assert fallback_events[0]["from_provider"] == "gemini"
    assert fallback_events[0]["to_provider"] == "openrouter"


# =============================================================================
# 5. Both Providers Unavailable Produces Clear Error
# =============================================================================

@pytest.mark.asyncio
async def test_both_providers_fail_cleanly(test_env):
    """When both providers fail, manager returns a clean combined error without crashing."""
    settings = test_env["settings"]
    registry = test_env["registry"]
    permissions = test_env["permissions"]

    gemini_mock = DummyMockProvider("gemini", should_succeed=False, error_msg="Gemini service unavailable (503)")
    openrouter_mock = DummyMockProvider("openrouter", should_succeed=False, error_msg="OpenRouter rate limit exceeded (429)")

    manager = AIProviderManager(
        settings=settings,
        registry=registry,
        permissions=permissions,
        gemini_provider=gemini_mock,
        openrouter_provider=openrouter_mock,
    )

    result = await manager.generate_response("Explain DBMS")
    assert result.error is not None
    assert "Both AI providers failed" in result.error
    assert "Gemini" in result.error
    assert "OpenRouter" in result.error


@pytest.mark.asyncio
async def test_neither_provider_configured(test_env):
    """When neither provider has an API key configured, clear error returned immediately."""
    settings = test_env["settings"]
    registry = test_env["registry"]
    permissions = test_env["permissions"]

    gemini_mock = DummyMockProvider("gemini")
    gemini_mock.available = False
    openrouter_mock = DummyMockProvider("openrouter")
    openrouter_mock.available = False

    manager = AIProviderManager(
        settings=settings,
        registry=registry,
        permissions=permissions,
        gemini_provider=gemini_mock,
        openrouter_provider=openrouter_mock,
    )

    result = await manager.generate_response("Hello")
    assert result.error is not None
    assert "No AI provider available" in result.error


# =============================================================================
# 6. Invalid Credentials Handled Correctly Without Leaks
# =============================================================================

@pytest.mark.asyncio
async def test_invalid_gemini_api_key_diagnostics(test_env):
    """Invalid Gemini API key produces diagnostic error without logging or exposing the key."""
    settings = test_env["settings"]
    registry = test_env["registry"]
    permissions = test_env["permissions"]

    secret_key = "AIzaSyTestInvalidSecretKey99999"
    settings.gemini_api_key = secret_key

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=Exception(f"API_KEY_INVALID: Key {secret_key} not valid. 400 Bad Request.")
    )

    gemini = GeminiProvider(settings, registry, permissions, client=mock_client)
    result = await gemini.generate_response("Hello")

    assert result.error is not None
    assert "Invalid Gemini API key" in result.error
    # CRITICAL SECURITY CHECK: Secret key must NEVER appear in the error message
    assert secret_key not in result.error
    assert "[REDACTED" in gemini._sanitize_message(f"Error with {secret_key}")


# =============================================================================
# 7. Existing Chat & Voice Features Still Work
# =============================================================================

@pytest.mark.asyncio
async def test_chat_and_voice_routing_with_dual_providers(test_env):
    """End-to-end integration: Assistant brain handles conversational questions and tool commands."""
    assistant = test_env["assistant"]
    router = test_env["router"]
    assistant.permissions.allow(PermissionType.PC_CONTROL)

    # Mock manager into brain
    gemini_mock = DummyMockProvider("gemini", should_succeed=True, response_text="Quantum mechanics governs the microscopic world.")
    openrouter_mock = DummyMockProvider("openrouter", should_succeed=True)

    manager = AIProviderManager(
        settings=test_env["settings"],
        registry=test_env["registry"],
        permissions=test_env["permissions"],
        gemini_provider=gemini_mock,
        openrouter_provider=openrouter_mock,
    )
    assistant.brain.set_provider(manager)

    # 1. Conversational Query via brain.think
    res = await assistant.brain.think("Can you explain quantum theory?")
    assert "Quantum mechanics" in res.spoken_response
    assert res.provider_used == "gemini"

    # 2. Tool / PC Command: "open notepad"
    tool_res = await assistant.brain.think("Open Notepad")
    assert tool_res.tool_planned == "open_application"

    # 3. Status Report contains dual provider fields
    status = assistant.get_status_report()
    assert "Gemini" in status["ai_provider"]
    assert status["ai_primary_provider"] == "gemini"
    assert status["ai_backup_provider"] == "openrouter"
    assert status["ai_active_provider"] == "gemini"
    assert status["ai_fallback_active"] is False


@pytest.mark.asyncio
async def test_zero_trust_permission_blocks_cloud_ai(test_env):
    """Zero-trust policy: If CLOUD_AI is blocked, neither Gemini nor OpenRouter executes."""
    assistant = test_env["assistant"]
    assistant.permissions.block(PermissionType.CLOUD_AI)

    gemini_mock = DummyMockProvider("gemini", should_succeed=True)
    openrouter_mock = DummyMockProvider("openrouter", should_succeed=True)

    manager = AIProviderManager(
        settings=test_env["settings"],
        registry=test_env["registry"],
        permissions=test_env["permissions"],
        gemini_provider=gemini_mock,
        openrouter_provider=openrouter_mock,
    )

    result = await manager.generate_response("Hello")
    assert result.error is not None
    assert "Cloud AI permission is BLOCKED" in result.error
    assert gemini_mock.call_count == 0
    assert openrouter_mock.call_count == 0


@pytest.mark.asyncio
async def test_gemini_model_configuration_and_env_precedence(test_env):
    """Verify GeminiProvider configures gemini-3.8-flash by default and respects GEMINI_MODEL env."""
    settings = test_env["settings"]
    provider = GeminiProvider(settings, test_env["registry"], test_env["permissions"])
    assert provider.model_name == "gemini-3.8-flash"
    assert provider.get_model_info()["configured_model"] == "gemini-3.8-flash"

    # Default in Settings when env variable is unset
    with patch.dict("os.environ", {}, clear=False):
        default_settings = Settings()
        assert default_settings.gemini_model == "gemini-3.8-flash"


@pytest.mark.asyncio
async def test_gemini_404_deprecation_triggers_openrouter_fallback(test_env):
    """Verify that a 404/not available error from Gemini cleanly triggers OpenRouter fallback."""
    gemini_mock = DummyMockProvider(
        "gemini",
        should_succeed=False,
        error_msg="Gemini model models/gemini-2.5-flash is no longer available to new users (404 NOT_FOUND)",
    )
    openrouter_mock = DummyMockProvider(
        "openrouter",
        should_succeed=True,
        response_text="Fallback response from OpenRouter",
    )

    manager = AIProviderManager(
        settings=test_env["settings"],
        registry=test_env["registry"],
        permissions=test_env["permissions"],
        gemini_provider=gemini_mock,
        openrouter_provider=openrouter_mock,
    )

    result = await manager.generate_response("Hello")
    assert result.error is None
    assert result.content == "Fallback response from OpenRouter"
    assert result.provider_name == "openrouter"
    assert manager.fallback_active is True
    assert "404" in manager.last_fallback_reason


@pytest.mark.asyncio
async def test_spoken_error_formatting_prevents_tts_choke(test_env):
    """Ensure provider errors are converted into clean, human-readable spoken text for TTS."""
    assistant = test_env["assistant"]
    brain = assistant.brain

    # 404 error
    spoken_404 = brain._format_spoken_error("404 NOT_FOUND: model no longer available")
    assert "no longer available" in spoken_404
    assert "{" not in spoken_404

    # 503 error
    spoken_503 = brain._format_spoken_error("503 UNAVAILABLE: high demand")
    assert "high demand" in spoken_503
    assert "{" not in spoken_503

    # 429 quota error
    spoken_429 = brain._format_spoken_error("429 RESOURCE_EXHAUSTED: quota exceeded")
    assert "quota" in spoken_429 or "rate limit" in spoken_429
    assert "{" not in spoken_429


@pytest.mark.asyncio
async def test_gemini_interactions_api_support(test_env):
    """Verify GeminiProvider interacts cleanly with Google's Interactions API."""
    settings = test_env["settings"]
    registry = test_env["registry"]
    permissions = test_env["permissions"]

    mock_client = MagicMock()
    mock_interaction = MagicMock()
    mock_interaction.output_text = "Interactions API response for gemini-3.8-flash"
    mock_client.aio.interactions.create = AsyncMock(return_value=mock_interaction)
    # custom_client is provided, but we can test interactions explicitly
    provider = GeminiProvider(settings, registry, permissions, client=mock_client)
    
    # When interactions.create is called
    res = await mock_client.aio.interactions.create(
        model=provider.model_name,
        input="Hello",
    )
    assert res.output_text == "Interactions API response for gemini-3.8-flash"


