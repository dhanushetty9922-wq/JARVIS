"""JARVIS Local AI Provider (Phase 4).

Interacts with local model runtimes (Ollama, llama.cpp, LM Studio) via standard
HTTP REST endpoints without permanent background memory overhead.

HARDWARE & PRIVACY CONSTRAINTS (8 GB RAM LAPTOP):
- DO NOT automatically download or install a large local LLM.
- If no local model is running, clearly report: 'Local AI provider is not configured.'
- Never keep a heavy model permanently locked in RAM.
- All inference happens 100% locally with zero external network transmission.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from ai.provider import AIResult, BaseAIProvider
from ai.tool_call_parser import ToolCallParser
from config import Settings
from tools.registry import ToolRegistry

logger = logging.getLogger("jarvis.ai.local")

# Models exceeding 4 Billion parameters are prohibited on 8 GB RAM laptops
HEAVY_MODEL_PATTERNS = ["7b", "8b", "13b", "14b", "27b", "32b", "70b"]


def is_heavy_model(model_name: str) -> bool:
    """Return True if model size exceeds the 8 GB RAM laptop safety budget."""
    lower = model_name.lower()
    for pattern in HEAVY_MODEL_PATTERNS:
        if re.search(rf"(?:^|[:\-_]){pattern}(?:$|[:\-_])", lower):
            return True
    return False


# Recommended lightweight local models suitable for 8 GB RAM Windows laptop
LIGHTWEIGHT_MODEL_RECOMMENDATIONS: List[Dict[str, Any]] = [
    {
        "name": "qwen2.5:1.5b",
        "parameters": "1.5 Billion",
        "download_size": "~1.0 GB",
        "expected_ram": "~1.5 GB",
        "strengths": "Fast response, low RAM footprint, excellent structured tool calling & JSON output.",
        "recommended": True,
    },
    {
        "name": "llama3.2:1b",
        "parameters": "1.0 Billion",
        "download_size": "~1.3 GB",
        "expected_ram": "~1.8 GB",
        "strengths": "Meta's lightweight model, low latency, solid natural language comprehension.",
        "recommended": False,
    },
    {
        "name": "phi3:mini",
        "parameters": "3.8 Billion",
        "download_size": "~2.3 GB",
        "expected_ram": "~3.0 GB",
        "strengths": "Microsoft Phi-3 reasoning architecture, compact size.",
        "recommended": False,
    },
]


class LocalAIProvider(BaseAIProvider):
    """Local AI provider communicating with local server (Ollama / llama.cpp)."""

    name = "local"

    def __init__(self, settings: Settings, registry: ToolRegistry):
        self.settings = settings
        self.registry = registry
        self.parser = ToolCallParser(registry)
        self.endpoint = settings.local_model_endpoint.rstrip("/")
        self.model_name = settings.local_model_name

    def is_available(self) -> bool:
        """Check if local AI server is running and reachable within 1 second."""
        try:
            url = f"{self.endpoint}/api/tags"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass

        # Try OpenAI-compatible endpoint format (LM Studio / vLLM / llama-cpp-python)
        try:
            url = f"{self.endpoint}/v1/models"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass

        return False

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AIResult:
        """Query local AI model for tool planning or conversational answer."""
        # 1. Enforce 8 GB RAM laptop safety constraint
        if is_heavy_model(self.model_name):
            msg = (
                f"Model '{self.model_name}' is blocked by 8 GB RAM safety policy. "
                "Large 7B/8B+ models exceed the laptop memory limit and cause severe system freezing. "
                "Please use a lightweight model like 'qwen2.5:1.5b' (< 1.5 GB RAM)."
            )
            logger.warning(msg)
            return AIResult.fail(msg, provider=self.name, model=self.model_name)

        # 2. Verify availability first without downloading anything
        if not self.is_available():
            msg = (
                "Local AI provider is not configured. "
                f"No local model server is reachable at {self.endpoint}. "
                "JARVIS does not automatically download models to protect your 8 GB RAM."
            )
            logger.info(msg)
            return AIResult.fail(msg, provider=self.name, model=self.model_name)

        # 3. Execute local request in background thread
        loop = asyncio.get_event_loop()
        try:
            raw_text = await loop.run_in_executor(
                None,
                self._send_request_sync,
                prompt,
                system_prompt,
                tools,
            )
            return self.parser.parse_raw_response(raw_text, provider_name=self.name, model_name=self.model_name)
        except Exception as e:
            logger.error(f"Local AI inference error: {e}")
            return AIResult.fail(f"Local AI inference failed: {e}", provider=self.name, model=self.model_name)

    def _send_request_sync(
        self,
        prompt: str,
        system_prompt: Optional[str],
        tools: Optional[List[Dict[str, Any]]],
    ) -> str:
        """Synchronous HTTP call to local model endpoint."""
        url = f"{self.endpoint}/api/generate"
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.settings.ai_temperature,
                "num_predict": self.settings.ai_max_tokens,
                "num_ctx": 2048,  # Constrain context window to 2048 to keep RAM under 1.5 GB
            },
        }

        if system_prompt:
            payload["system"] = system_prompt

        json_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=json_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "")

    def get_model_info(self) -> Dict[str, Any]:
        """Return diagnostic metadata about current local AI configuration."""
        available = self.is_available()
        return {
            "provider": self.name,
            "configured_model": self.model_name,
            "endpoint": self.endpoint,
            "server_reachable": available,
            "status": "ONLINE (Local)" if available else "NOT CONFIGURED (Server unreachable)",
            "auto_download_prevented": True,
            "laptop_ram_optimized": True,
            "ram_budget": "< 1.8 GB RAM (8 GB laptop safe)",
            "context_window_limit": 2048,
        }

    @staticmethod
    def get_lightweight_recommendations() -> List[Dict[str, Any]]:
        """Return structured lightweight model recommendations for 8 GB RAM laptop."""
        return LIGHTWEIGHT_MODEL_RECOMMENDATIONS
