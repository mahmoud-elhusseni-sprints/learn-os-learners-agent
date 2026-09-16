"""Command registry for employer-facing graph investigations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.app.agents.talent_intelligence.registry import TOOL_FUNCTIONS
from src.app.schemas.models import ToolResult

GraphCommand = Callable[..., ToolResult]

COMMANDS: dict[str, GraphCommand] = dict(TOOL_FUNCTIONS)


def get_command(name: str) -> GraphCommand | None:
    """Return a registered graph command without executing untrusted names."""
    return COMMANDS.get(name)


def run_command(name: str, *args: Any, **kwargs: Any) -> ToolResult:
    """Execute a registered command and report unknown commands uniformly."""
    command = get_command(name)
    if command is None:
        return ToolResult("error", None, f"Unknown graph command: {name}")
    return command(*args, **kwargs)


__all__ = ["COMMANDS", "GraphCommand", "get_command", "run_command"]
