"""Shared schemas; SQL models are loaded only when explicitly requested."""

from importlib import import_module
from typing import Any

from src.app.schemas.models import (
    AssessmentAnswer,
    AssessmentPayload,
    Confidence,
    ConversationState,
    DataSource,
    DataSourceType,
    LearnerProfile,
    MemoryCard,
    MetricDraft,
    NonEmpty,
    ProfileMetric,
    ProfileUpdateInput,
    ReviewPayload,
    RubricPointEvaluation,
    ToolResult,
)

__all__ = [
    "User",
    "ConversationSession",
    "Message",
    "NonEmpty",
    "Confidence",
    "ToolResult",
    "ConversationState",
    "MemoryCard",
    "MetricDraft",
    "ProfileMetric",
    "LearnerProfile",
    "DataSourceType",
    "RubricPointEvaluation",
    "ReviewPayload",
    "AssessmentAnswer",
    "AssessmentPayload",
    "DataSource",
    "ProfileUpdateInput",
]


def __getattr__(name: str) -> Any:
    modules = {
        "User": "user",
        "ConversationSession": "conversation",
        "Message": "message",
    }
    if name not in modules:
        raise AttributeError(name)
    return getattr(import_module(f"src.app.models.{modules[name]}"), name)
