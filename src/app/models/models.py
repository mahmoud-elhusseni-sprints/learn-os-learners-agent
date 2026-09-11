from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated, Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

NonEmpty = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]
Confidence = Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False, strict=True)]


@dataclass
class ToolResult:
    status: str
    data: Any
    message: str = ""


@dataclass
class ConversationState:
    active_learner_id: str | None = None
    turns: list[dict[str, str]] = field(default_factory=list)
    last_tool_calls: list[dict[str, Any]] = field(default_factory=list)


class MemoryCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_id: NonEmpty
    meeting_id: Optional[Union[NonEmpty, str]] = None
    metric_key: NonEmpty
    content: NonEmpty
    rationale: Optional[str] = Field(default="", description="Rationale explanation")
    tags: list[NonEmpty] = Field(
        default_factory=list, description="Predefined competency tags"
    )
    created_at: Optional[AwareDatetime] = Field(
        default=None, description="Creation timestamp"
    )
    associated_learner_ids: list[str] = Field(
        default_factory=list,
        description="List of LearnerProfile UUIDs linked to this card (Many-to-Many)",
    )
    source_datasource_id: Optional[str] = Field(
        default=None,
        description=(
            "datasource_id of the DataSource record this card was distilled "
            "from, if any. Lets the graph loader draw the EXTRACTED_INTO "
            "edge (DataSource -> MemoryCard) precisely instead of guessing."
        ),
    )

    @field_validator("card_id", "meeting_id", mode="before")
    @classmethod
    def normalize_uuid(cls, value: Any) -> Any:
        """Accept UUID objects as well as nonempty string identifiers."""
        return str(value) if isinstance(value, UUID) else value


class MetricDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: NonEmpty
    confidence: Confidence


class ProfileMetric(MetricDraft):
    model_config = ConfigDict(extra="allow")
    evidence_ids: list[NonEmpty] = Field(default_factory=list)


class LearnerProfile(BaseModel):
    model_config = ConfigDict(extra="allow")

    learner_id: Optional[str] = Field(
        default=None, description="Unique UUID for the learner"
    )
    name: Optional[str] = Field(default=None, description="Learner name/pseudonym")
    role: str = Field(default="member", description="Team role (lead/member)")
    group_name: Optional[str] = Field(default=None, description="Internship track name")
    round_name: Optional[str] = Field(
        default=None, description="Internship round label"
    )
    added_at: Optional[str] = Field(
        default=None, description="ISO timestamp when learner joined"
    )
    learner_status: Optional[str] = Field(
        default=None, description="Active status indicator"
    )
    metrics: dict[NonEmpty, ProfileMetric] = Field(
        default_factory=dict, description="Consolidated competency metrics"
    )


class ProfileUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    previous_profile: Optional[LearnerProfile] = None
    memory_cards: list[MemoryCard] = Field(default_factory=list)


class DataSourceType(str, Enum):
    REVIEW = "review"
    ASSESSMENTS = "assessments"
    CHAT = "chat"
    MEETINGS = "meetings"


class RubricPointEvaluation(BaseModel):
    rubric_id: Optional[int] = Field(default=None, description="Rubric item ID")
    category: str = Field(
        default="digital_ai_skills", description="Competency taxonomy category"
    )
    requirement: str = Field(default="", description="Task requirement string")
    status: str = Field(..., description="Pass status: Yes, No, Partial")
    evaluation_criteria: Optional[str] = Field(
        default=None, description="Evaluation criterion description"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Qualitative explanation why point passed/failed",
    )
    confidence_score: Optional[float] = Field(
        default=None, description="Grader confidence score"
    )


class ReviewPayload(BaseModel):
    lx_id: str = Field(..., description="Task Learning Experience UUID")
    task_headline: Optional[str] = Field(
        default=None, description="Task headline title"
    )
    attempt_number: int = Field(
        default=1, description="Submission review attempt number"
    )
    hours_before_deadline: Optional[float] = Field(
        default=None, description="Hours before deadline"
    )
    submission_text: Optional[str] = Field(
        default="", description="Learner submission text"
    )
    assets: List[str] = Field(
        default_factory=list,
        description="Combined code repositories and media assets",
    )
    verdict: str = Field(..., description="Overall verdict: passed, failed, retry")
    feedback_summary: Optional[str] = Field(
        default="", description="Mentor review summary"
    )
    mentor_reply: Optional[str] = Field(
        default=None, description="Direct mentor reply text"
    )
    detailed_rubric_evaluations: List[RubricPointEvaluation] = Field(
        default_factory=list,
        description="Evaluations for each rubric point of this task",
    )


class AssessmentAnswer(BaseModel):
    question_id: str = Field(..., description="Question identifier")
    domain: Optional[str] = Field(default=None, description="Domain topic")
    metric_key: Optional[str] = Field(default=None, description="Competency metric key")
    learner_answer: str = Field(..., description="Learner's answer text")
    score: Optional[float] = Field(default=None, description="Question score")
    evaluation_notes: Optional[str] = Field(default=None, description="Grader notes")


class AssessmentPayload(BaseModel):
    lx_id: Optional[str] = Field(default=None, description="Task / Assessment UUID")
    assessment_type: Optional[str] = Field(
        default="pre_course", description="pre_course / post_course"
    )
    topic_id: Optional[str] = Field(
        default=None, description="Topic/Archetype identifier"
    )
    score: Optional[float] = Field(
        default=None, description="Explicit assessment numerical score"
    )
    max_score: Optional[float] = Field(
        default=100.0, description="Maximum possible assessment score"
    )
    answers: List[AssessmentAnswer] = Field(
        default_factory=list, description="Question evaluations"
    )


class DataSource(BaseModel):
    datasource_id: str = Field(
        ..., description="Unique UUID for this data source event"
    )
    datasource_name: Union[DataSourceType, str] = Field(
        ..., description="'review', 'assessments', 'chat', 'meetings'"
    )
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    learner_id: Optional[str] = Field(
        default=None,
        description="Learner UUID who produced/underwent this data source",
    )
    payload: Union[ReviewPayload, AssessmentPayload, Dict[str, Any]] = Field(
        ..., description="Polymorphic payload depending on datasource_name"
    )

    @classmethod
    def generate_deterministic_id(
        cls,
        learner_id: str,
        lx_id: str,
        timestamp: str,
        source_type: str,
        attempt: int = 1,
    ) -> str:
        """Generate a deterministic SHA-256 hash-based ID for data sources."""
        raw_key = f"{learner_id}:{lx_id}:{timestamp}:{source_type}:{attempt}"
        return "ds_" + hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:24]


__all__ = [
    "NonEmpty",
    "Confidence",
    "ToolResult",
    "ConversationState",
    "MemoryCard",
    "MetricDraft",
    "ProfileMetric",
    "LearnerProfile",
    "ProfileUpdateInput",
    "DataSourceType",
    "RubricPointEvaluation",
    "ReviewPayload",
    "AssessmentAnswer",
    "AssessmentPayload",
    "DataSource",
]
