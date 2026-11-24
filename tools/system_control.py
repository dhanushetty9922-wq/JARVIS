"""JARVIS Safe System Control Tools (Phase 1).

Includes read-only system diagnostic tools for Phase 1.
Destructive operations (shutdown, restart, lock) are explicitly deferred to later phases.
"""

from __future__ import annotations

import platform
import psutil
from typing import Any, Dict
from pydantic import BaseModel, Field

from config import PermissionType, RiskLevel
from tools.base_tool import BaseTool, EmptyParams, ToolResult


class SystemMetricsParams(BaseModel):
    """Optional filter parameters for system metrics."""
    include_battery: bool = Field(default=True, description="Whether to include battery percentage.")
    include_memory: bool = Field(default=True, description="Whether to include RAM usage.")
    include_cpu: bool = Field(default=True, description="Whether to include CPU percentage.")


class SystemStatusTool(BaseTool):
    """Read-only tool that queries system diagnostics (CPU, RAM, Battery, OS)."""

    name = "system_status"
    description = "Provides read-only hardware metrics including CPU, RAM, battery, and platform info."
    input_schema = SystemMetricsParams
    required_permission = None  # Read-only health metrics permitted
    risk_level = RiskLevel.LOW

    async def run(
        self,
        include_battery: bool = True,
        include_memory: bool = True,
        include_cpu: bool = True,
        **kwargs: Any,
    ) -> ToolResult:
        metrics: Dict[str, Any] = {
            "os": f"{platform.system()} {platform.release()}",
            "computer_name": platform.node(),
            "windows_version": f"{platform.system()} {platform.release()} (Build {platform.version()})",
            "processor": platform.processor(),
        }

        if include_cpu:
            metrics["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            metrics["cpu_count"] = psutil.cpu_count(logical=True)

        if include_memory:
            vmem = psutil.virtual_memory()
            metrics["memory"] = {
                "total_gb": round(vmem.total / (1024**3), 2),
                "used_gb": round(vmem.used / (1024**3), 2),
                "percent": vmem.percent,
            }

        # Disk space (C: drive)
        try:
            disk = psutil.disk_usage("C:\\")
            metrics["disk"] = {
                "drive": "C:",
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent_used": disk.percent,
            }
        except Exception:
            metrics["disk"] = "Unable to read disk usage"

        if include_battery:
            battery = psutil.sensors_battery()
            if battery:
                metrics["battery"] = {
                    "percent": battery.percent,
                    "power_plugged": battery.power_plugged,
                    "secs_left": battery.secsleft,
                }
            else:
                metrics["battery"] = "No battery sensor detected (Desktop or AC power)."

        return ToolResult.ok(
            message="System diagnostics retrieved successfully.",
            data=metrics,
        )


class EchoParams(BaseModel):
    """Parameters for Echo test tool."""
    message: str = Field(description="Message string to echo back.")


class EchoTool(BaseTool):
    """Safe echo tool used for verifying pipeline routing and schema validation."""

    name = "echo"
    description = "Echoes back the input message for pipeline verification."
    input_schema = EchoParams
    required_permission = None
    risk_level = RiskLevel.LOW

    async def run(self, message: str, **kwargs: Any) -> ToolResult:
        return ToolResult.ok(
            message=f"Echo: {message}",
            data={"echoed_text": message},
        )
