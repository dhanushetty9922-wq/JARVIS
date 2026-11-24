"""JARVIS Google Gemini AI Provider.

Integrates the official Google Gemini API using the google-genai SDK.

STRICT PRIVACY & SECURITY RULES:
- Gated behind PermissionManager: Must have 'cloud_ai' permission ALLOWED.
- NEVER sends audio recordings, screen buffers, or unrelated personal files.
- API keys are NEVER printed, logged, or exposed in error messages.
- Masked API key representation (e.g. 'AIzaSy...wxyz').
- All tool execution plans remain subject to central SecurityManager verification.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from ai.provider import AIResult, BaseAIProvider, ToolCallRequest
from ai.tool_call_parser import ToolCallParser
from config import PermissionType, Settings
from security.permission_manager import PermissionManager
from tools.registry import ToolRegistry

logger = logging.getLogger("jarvis.ai.gemini")


class GeminiProvider(BaseAIProvider):
    """Primary cloud provider connecting to Google Gemini API via official google-genai SDK."""

    name = "gemini"

    def __init__(
        self,
        settings: Settings,
        registry: ToolRegistry,
        permissions: PermissionManager,
        client: Optional[Any] = None,
    ):
        self.settings = settings
        self.registry = registry
        self.permissions = permissions
        self.parser = ToolCallParser(registry)
        self.model_name = settings.gemini_model or "gemini-3.8-flash"
        self._custom_client = client

    @property
    def api_key(self) -> Optional[str]:
        return self.settings.gemini_api_key

    def is_available(self) -> bool:
        """Check if Gemini is configured with an API key and permission."""
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

    def _sanitize_message(self, msg: str) -> str:
        """Strip API keys or sensitive auth parameters from strings."""
        if not msg:
            return ""
        if self.api_key and self.api_key.strip():
            msg = msg.replace(self.api_key.strip(), "[REDACTED_API_KEY]")
        # General regex sanitization for key patterns
        msg = re.sub(r'AIzaSy[A-Za-z0-9_-]{33}', '[REDACTED_GEMINI_KEY]', msg)
        msg = re.sub(r'sk-or-v1-[A-Za-z0-9_-]{32,}', '[REDACTED_OPENROUTER_KEY]', msg)
        return msg

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AIResult:
        """Send prompt to Gemini and parse structured tool plan or natural response."""
        # 1. Zero-Trust Permission Check: Cloud AI must be explicitly allowed
        if not self.permissions.is_allowed(PermissionType.CLOUD_AI):
            err_msg = "Cloud AI permission is BLOCKED. Run 'allow cloud_ai' first to enable online reasoning."
            logger.warning(err_msg)
            return AIResult.fail(err_msg, provider=self.name, model=self.model_name)

        # 2. Check API key presence
        if not self.api_key or not self.api_key.strip():
            err_msg = "Gemini API key is not configured. Set GEMINI_API_KEY in your .env file."
            logger.warning(err_msg)
            return AIResult.fail(err_msg, provider=self.name, model=self.model_name)

        # 3. Build SDK Client with strict non-hanging timeout and no indefinite retries
        http_opts = types.HttpOptions(
            retry_options=types.HttpRetryOptions(attempts=1),
            timeout=15000,
        )
        client = self._custom_client or genai.Client(api_key=self.api_key.strip(), http_options=http_opts)

        # 4. Convert tool schemas if provided
        gemini_tools: Optional[List[types.Tool]] = None
        if tools:
            func_declarations: List[types.FunctionDeclaration] = []
            for t in tools:
                fn = t.get("function", {})
                name = fn.get("name")
                if name:
                    func_declarations.append(
                        types.FunctionDeclaration(
                            name=name,
                            description=fn.get("description", ""),
                            parameters=fn.get("parameters"),
                        )
                    )
            if func_declarations:
                gemini_tools = [types.Tool(function_declarations=func_declarations)]

        # 5. Build GenerateContentConfig
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=self.settings.ai_temperature,
            max_output_tokens=self.settings.ai_max_tokens,
            tools=gemini_tools,
        )

        timeout_limit = min(float(getattr(self.settings, "gemini_timeout_seconds", 30.0)), 45.0)

        # 6. Execute asynchronous generation with strict execution timeout
        try:
            # Use Google's documented Interactions API when available and no function tools requested
            if hasattr(client.aio, "interactions") and not gemini_tools and not self._custom_client:
                interaction = await asyncio.wait_for(
                    client.aio.interactions.create(
                        model=self.model_name,
                        input=prompt,
                        system_instruction=system_prompt,
                    ),
                    timeout=timeout_limit,
                )
                output_text = getattr(interaction, "output_text", None)
                if output_text is None:
                    steps = getattr(interaction, "steps", [])
                    if steps and hasattr(steps[-1], "content") and steps[-1].content:
                        output_text = getattr(steps[-1].content[0], "text", "")
                return self.parser.parse_raw_response(
                    output_text or "",
                    provider_name=self.name,
                    model_name=self.model_name,
                )
            else:
                response = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config=config,
                    ),
                    timeout=timeout_limit,
                )
                return self._parse_gemini_response(response)
        except asyncio.TimeoutError:
            err_msg = f"Gemini request timed out after {timeout_limit}s."
            logger.error(err_msg)
            return AIResult.fail(err_msg, provider=self.name, model=self.model_name)
        except Exception as e:
            raw_err = str(e)
            sanitized = self._sanitize_message(raw_err)
            err_lower = sanitized.lower()
            status_code = getattr(e, "code", None) or getattr(e, "status_code", None)

            logger.error(f"Gemini API error (code={status_code}): {sanitized}")

            # Specific classification of provider errors
            if "api_key_invalid" in err_lower or "api key not valid" in err_lower or ("400" in err_lower and "key" in err_lower):
                return AIResult.fail(
                    "Invalid Gemini API key. Please check GEMINI_API_KEY in your .env file.",
                    provider=self.name,
                    model=self.model_name,
                )
            elif "404" in err_lower or "not found" in err_lower or "not_found" in err_lower or "no longer available" in err_lower:
                return AIResult.fail(
                    f"Gemini model '{self.model_name}' not found or no longer available (404): {sanitized}",
                    provider=self.name,
                    model=self.model_name,
                )
            elif "429" in err_lower or "resource_exhausted" in err_lower or "quota" in err_lower or "too_many_requests" in err_lower:
                return AIResult.fail(
                    f"Gemini rate limit or quota exceeded (429): {sanitized}",
                    provider=self.name,
                    model=self.model_name,
                )
            elif any(code in err_lower for code in ("500", "502", "503", "504", "unavailable", "internal")):
                return AIResult.fail(
                    f"Gemini service unavailable: {sanitized}",
                    provider=self.name,
                    model=self.model_name,
                )
            elif "timeout" in err_lower or "timed out" in err_lower:
                return AIResult.fail(
                    "Gemini request timed out.",
                    provider=self.name,
                    model=self.model_name,
                )
            elif "connection" in err_lower or "network" in err_lower:
                return AIResult.fail(
                    f"Network error contacting Gemini: {sanitized}",
                    provider=self.name,
                    model=self.model_name,
                )

            return AIResult.fail(
                f"Gemini error: {sanitized}",
                provider=self.name,
                model=self.model_name,
            )

    def _parse_gemini_response(self, response: Any) -> AIResult:
        """Translate Google Gemini response into standardized AIResult."""
        if not response:
            return AIResult.conversational("No response received from Gemini model.", provider=self.name, model=self.model_name)

        # 1. Native Function Calling: check function_calls
        function_calls = getattr(response, "function_calls", None)
        if function_calls:
            validated_calls: List[ToolCallRequest] = []
            for fc in function_calls:
                name = getattr(fc, "name", "")
                raw_args = getattr(fc, "args", {})
                args = raw_args if isinstance(raw_args, dict) else (dict(raw_args) if raw_args else {})

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

        # 2. Text response: May contain conversational text or markdown JSON
        content = getattr(response, "text", "") or ""
        return self.parser.parse_raw_response(content, provider_name=self.name, model_name=self.model_name)

    def get_model_info(self) -> Dict[str, Any]:
        """Return diagnostic metadata about current Gemini AI configuration."""
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
