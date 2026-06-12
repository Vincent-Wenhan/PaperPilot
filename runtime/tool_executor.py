"""Safety-aware execution for registered deterministic tools."""

from __future__ import annotations

import inspect
import time
from typing import Any

from runtime.tool_registry import ToolRegistry
from schemas.tool_schema import SafetyLevel, ToolCall, ToolResult


class ToolExecutor:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def run(
        self,
        call: ToolCall,
        allow_safety_levels: set[SafetyLevel] | None = None,
    ) -> ToolResult:
        registered = self.registry.get(call.tool_name)
        if registered is None:
            return ToolResult(
                tool_name=call.tool_name,
                success=False,
                error=f"Unknown tool: {call.tool_name}",
            )
        spec = registered.spec
        if spec.allowed_agents and call.requested_by not in spec.allowed_agents:
            return ToolResult(
                tool_name=call.tool_name,
                success=False,
                error=f"Agent is not authorized for tool: {call.requested_by}",
                safety_level=spec.safety_level,
            )
        if spec.safety_level == "blocked":
            return ToolResult(
                tool_name=call.tool_name,
                success=False,
                error="Blocked tools cannot be executed.",
                safety_level="blocked",
            )
        allowed = allow_safety_levels or {"safe"}
        if spec.safety_level not in allowed:
            return ToolResult(
                tool_name=call.tool_name,
                success=False,
                error=f"Tool safety level requires approval: {spec.safety_level}",
                safety_level=spec.safety_level,
            )
        try:
            inspect.signature(registered.function).bind(**call.arguments)
        except TypeError as exc:
            return ToolResult(
                tool_name=call.tool_name,
                success=False,
                error=f"Invalid tool arguments: {exc}",
                safety_level=spec.safety_level,
            )

        started = time.monotonic()
        try:
            output: Any = registered.function(**call.arguments)
        except Exception as exc:
            return ToolResult(
                tool_name=call.tool_name,
                success=False,
                error=str(exc),
                safety_level=spec.safety_level,
                elapsed_seconds=time.monotonic() - started,
            )
        return ToolResult(
            tool_name=call.tool_name,
            success=True,
            output=output,
            safety_level=spec.safety_level,
            elapsed_seconds=time.monotonic() - started,
        )
