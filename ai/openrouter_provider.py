"""JARVIS OpenRouter Cloud AI Provider (Phase 4).

Provides optional, high-capability cloud reasoning via OpenRouter API.

STRICT PRIVACY & SECURITY RULES:
- Gated behind PermissionManager: Must have 'cloud_ai' permission ALLOWED.
- NEVER sends audio recordings, screen buffers, or unrelated personal files.
- API keys are NEVER printed, logged, or exposed in error messages.
- Masked API key representation (e.g. 'sk-or-v1-...wxyz').
- All tool execution plans remain subject to central SecurityManager verification.
"""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from ai.provider import AIResult, BaseAIProvider, ToolCallRequest
from ai.tool_call_parser import ToolCallParser
from config import PermissionType, Settings
from security.permission_manager import PermissionManager
from tools.registry import ToolRegistry

logger = logging.getLogger("jarvis.ai.openrouter")

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterProvider(BaseAIProvider):
    """Optional cloud provider connecting to OpenRouter API."""

    name = "openrouter"

    def __init__(
        self,
        settings: Settings,
        registry: ToolRegistry,
        permissions: PermissionManager,
    ):
        self.settings = settings
        self.registry = registry
        self.permissions = permissions
        self.parser = ToolCallParser(registry)
        self.model_name = settings.openrouter_model

    @property
    def api_key(self) -> Optional[str]:
        return self.settings.openrouter_api_key

    def is_available(self) -> bool:
        """Check if OpenRouter is configured with an API key and permission."""
        has_key = bool(self.api_key and self.api_key.strip())
        cloud_permitted = self.permissions.is_allowed(PermissionType.CLOUD_AI)
        return has_key and cloud_permitted

    def get_masked_key(self) -> str:
        """Return safe, non-sensitive masked representation of the API key."""
        if not self.api_key:
            return "NOT CONFIGURED"
        key = self.api_key.strip()
        if len(key) <= 8:
            return "***"
        return f"{key[:6]}...{key[-4:]}"

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AIResult:
        """Send prompt to OpenRouter and parse structured tool plan or response."""
        # 1. Zero-Trust Permission Check: Cloud AI must be explicitly allowed
        if not self.permissions.is_allowed(PermissionType.CLOUD_AI):
            err_msg = "Cloud AI permission is BLOCKED. Run 'allow cloud_ai' first to enable online reasoning."
            logger.warning(err_msg)
            return AIResult.fail(err_msg, provider=self.name, model=self.model_name)

        # 2. Check API key presence
        if not self.api_key or not self.api_key.strip():
            err_msg = "OpenRouter API key is not configured. Set OPENROUTER_API_KEY in your .env file."
            logger.warning(err_msg)
            return AIResult.fail(err_msg, provider=self.name, model=self.model_name)

        # 3. Execute HTTP request asynchronously in executor
        loop = asyncio.get_event_loop()
        try:
            raw_res = await loop.run_in_executor(
                None,
                self._call_openrouter_sync,
                prompt,
                system_prompt,
                tools,
            )
            return self._parse_openrouter_response(raw_res)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return AIResult.fail("OpenRouter authentication failed (401). Check OPENROUTER_API_KEY.", provider=self.name, model=self.model_name)
            elif e.code == 429:
                return AIResult.fail("OpenRouter rate limit exceeded (429). Please try again shortly.", provider=self.name, model=self.model_name)
            return AIResult.fail(f"OpenRouter HTTP Error ({e.code}): {e.reason}", provider=self.name, model=self.model_name)
        except urllib.error.URLError as e:
            return AIResult.fail(f"Network error contacting OpenRouter: {e.reason}", provider=self.name, model=self.model_name)
        except TimeoutError:
            return AIResult.fail("OpenRouter request timed out.", provider=self.name, model=self.model_name)
        except Exception as e:
            logger.error(f"Unexpected OpenRouter error: {e}")
            return AIResult.fail(f"OpenRouter error: {e}", provider=self.name, model=self.model_name)

    def _call_openrouter_sync(
        self,
        prompt: str,
        system_prompt: Optional[str],
        tools: Optional[List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """Perform synchronous HTTP POST to OpenRouter chat completions."""
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.settings.ai_temperature,
            "max_tokens": self.settings.ai_max_tokens,
        }

        # Include tool schemas if provided
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/jarvis-assistant",
            "X-Title": "JARVIS Personal Assistant",
        }

        json_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(OPENROUTER_API_URL, data=json_bytes, headers=headers, method="POST")

        with urllib.request.urlopen(req, timeout=20.0) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _parse_openrouter_response(self, response_data: Dict[str, Any]) -> AIResult:
        """Translate OpenAI-compatible OpenRouter completion payload into AIResult."""
        choices = response_data.get("choices", [])
        if not choices:
            return AIResult.conversational("No response received from cloud model.", provider=self.name, model=self.model_name)

        first_choice = choices[0]
        message = first_choice.get("message", {})

        # 1. Native function calling / tool_calls in message
        raw_tool_calls = message.get("tool_calls", [])
        if raw_tool_calls:
            validated_calls: List[ToolCallRequest] = []
            for tc in raw_tool_calls:
                fn = tc.get("function", {})
                name = fn.get("name", "")
                args_raw = fn.get("arguments", "{}")
                if isinstance(args_raw, str):
                    try:
                        args = json.loads(args_raw)
                    except json.JSONDecodeError:
                        args = {}
                else:
                    args = args_raw

                call_req, err = self.parser.validate_tool_call(name, args)
                if err:
                    return AIResult.fail(err, provider=self.name, model=self.model_name)
                if call_req:
                    validated_calls.append(call_req)

            if validated_calls:
                return AIResult(
                    tool_calls=validated_calls,
                    provider_name=self.name,
                    model_name=self.model_name,
                )

        # 2. Text response: May contain embedded JSON or conversational response
        content = message.get("content") or ""
        return self.parser.parse_raw_response(content, provider_name=self.name, model_name=self.model_name)

    def get_model_info(self) -> Dict[str, Any]:
        """Return diagnostic metadata about current cloud AI configuration."""
        key_configured = bool(self.api_key and self.api_key.strip())
        cloud_permitted = self.permissions.is_allowed(PermissionType.CLOUD_AI)
        return {
            "provider": self.name,
            "configured_model": self.model_name,
            "api_key_status": "CONFIGURED" if key_configured else "NOT CONFIGURED",
            "api_key_masked": self.get_masked_key(),
            "cloud_ai_permission": "ALLOWED" if cloud_permitted else "BLOCKED",
            "provider_available": key_configured and cloud_permitted,
        }
