"""Tests for JARVIS Tool Registry and Foundation Tools."""

import pytest
from tools.base_tool import BaseTool, EmptyParams, ToolResult
from tools.registry import ToolRegistry
from tools.system_control import EchoTool, SystemStatusTool
from config import RiskLevel


@pytest.fixture
def registry():
    reg = ToolRegistry()
    reg.register(SystemStatusTool())
    reg.register(EchoTool())
    return reg


def test_registry_lookup(registry: ToolRegistry):
    """Test lookup and listing in registry."""
    assert registry.has("system_status")
    assert registry.has("echo")
    assert not registry.has("unknown_tool")

    tool = registry.get("echo")
    assert tool is not None
    assert tool.name == "echo"
    assert tool.risk_level == RiskLevel.LOW


def test_registry_metadata_and_ai_schemas(registry: ToolRegistry):
    """Verify tool metadata and AI function calling schema formats."""
    meta = registry.get_metadata_list()
    assert len(meta) == 2
    assert any(m["name"] == "system_status" for m in meta)

    schemas = registry.get_ai_schemas()
    assert len(schemas) == 2
    for s in schemas:
        assert s["type"] == "function"
        assert "name" in s["function"]
        assert "description" in s["function"]
        assert "parameters" in s["function"]


@pytest.mark.asyncio
async def test_system_status_tool_execution():
    """Verify SystemStatusTool returns valid hardware diagnostics."""
    tool = SystemStatusTool()
    result = await tool.run(include_battery=True, include_memory=True, include_cpu=True)
    assert result.success is True
    assert "data" in result.model_dump()
    data = result.data
    assert "os" in data
    assert "cpu_percent" in data
    assert "memory" in data


@pytest.mark.asyncio
async def test_echo_tool_execution():
    """Verify EchoTool correctly returns echoed string."""
    tool = EchoTool()
    result = await tool.run(message="JARVIS Online")
    assert result.success is True
    assert result.data["echoed_text"] == "JARVIS Online"
