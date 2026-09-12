"""Command registry for employer-facing graph investigations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.app.agents.talent_intelligence import tools
from src.app.models.models import ToolResult

GraphCommand = Callable[..., ToolResult]

COMMANDS: dict[str, GraphCommand] = {
    "get_learner_profile": tools.get_learner_profile,
    "get_skill_proofs": tools.get_skill_proofs,
    "get_behavioral_context": tools.get_behavioral_context,
    "get_strengths_and_gaps": tools.get_strengths_and_gaps,
    "get_milestone_history": tools.get_milestone_history,
    "investigate_employer": tools.investigate_employer,
    "suggest_next_steps": tools.suggest_next_steps,
}


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
