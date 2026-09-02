"""Data contracts for the Talent Intelligence Agent.

The contracts intentionally do not expose JSONL-specific implementation details.
The same shapes can be returned by a future Neo4j adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    status: str
    data: Any
    message: str = ""


@dataclass
class EvidenceRecord:
    evidence_id: str
    learner_id: str
    source_type: str
    source_ref: str
    date: str | None
    observation: str
    context: str
    tags: list[str] = field(default_factory=list)
    metric_key: str | None = None


@dataclass
class LearnerProfile:
    learner_id: str
    name: str
    email: str | None
    group_id: str | None
    group_name: str | None
    round_name: str | None
    learner_status: str | None


@dataclass
class Milestone:
    event_id: str
    date: str | None
    summary: str
    tags: list[str]
    source_type: str
    context: str


@dataclass
class ConversationState:
    active_learner_id: str | None = None
    turns: list[dict[str, str]] = field(default_factory=list)
    last_tool_calls: list[dict[str, Any]] = field(default_factory=list)
