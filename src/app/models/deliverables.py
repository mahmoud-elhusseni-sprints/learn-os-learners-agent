import hashlib
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, model_validator


class LearnerProfile(BaseModel):
    learner_id: str = Field(..., description="Unique UUID for the learner")
    name: str = Field(..., description="Learner name/pseudonym")
    role: str = Field(default="member", description="Team role (lead/member)")
    group_name: str = Field(..., description="Internship track name")
    round_name: str = Field(..., description="Internship round label")
    added_at: Optional[str] = Field(
        None, description="ISO timestamp when learner joined"
    )
    learner_status: Optional[str] = Field(None, description="Active status indicator")


class DataSourceType(str, Enum):
    REVIEW = "review"
    ASSESSMENTS = "assesments"
    CHAT = "chat"
    MEETINGS = "meetings"


class RubricPointEvaluation(BaseModel):
    rubric_id: Optional[int] = Field(None, description="Rubric item ID")
    category: str = Field(
        default="digital_ai_skills", description="Competency taxonomy category"
    )
    requirement: str = Field(default="", description="Task requirement string")
    status: str = Field(..., description="Pass status: Yes, No, Partial")
    evaluation_criteria: Optional[str] = Field(
        None, description="Evaluation criterion description"
    )
    reason: Optional[str] = Field(
        None, description="Qualitative explanation why point passed/failed"
    )
    confidence_score: Optional[float] = Field(
        None, description="Grader confidence score"
    )


class ReviewPayload(BaseModel):
    lx_id: str = Field(..., description="Task Learning Experience UUID")
    task_headline: Optional[str] = Field(None, description="Task headline title")
    attempt_number: int = Field(
        default=1, description="Submission review attempt number"
    )
    hours_before_deadline: Optional[float] = Field(
        None, description="Hours before deadline"
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
    mentor_reply: Optional[str] = Field(None, description="Direct mentor reply text")
    detailed_rubric_evaluations: List[RubricPointEvaluation] = Field(
        default_factory=list,
        description="Evaluations for each rubric point of this task",
    )


class AssessmentAnswer(BaseModel):
    question_id: str = Field(..., description="Question identifier")
    domain: Optional[str] = Field(None, description="Domain topic")
    metric_key: Optional[str] = Field(None, description="Competency metric key")
    learner_answer: str = Field(..., description="Learner's answer text")
    score: Optional[float] = Field(None, description="Question score")
    evaluation_notes: Optional[str] = Field(None, description="Grader notes")


class AssessmentPayload(BaseModel):
    lx_id: Optional[str] = Field(None, description="Task / Assessment UUID")
    assessment_type: Optional[str] = Field(
        default="pre_course", description="pre_course / post_course"
    )
    topic_id: Optional[str] = Field(None, description="Topic/Archetype identifier")
    score: Optional[float] = Field(
        None, description="Explicit assessment numerical score"
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
        ..., description="'review', 'assesments', 'chat', 'meetings'"
    )
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    learner_id: Optional[str] = Field(
        None,
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
        raw_key = f"{learner_id}:{lx_id}:{timestamp}:{source_type}:{attempt}"
        return "ds_" + hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:24]


class MemoryCard(BaseModel):
    card_id: str = Field(..., description="Unique memory card UUID")
    metric_key: str = Field(..., description="Competency metric key")
    content: str = Field(..., description="Summary content")
    rationale: Optional[str] = Field(None, description="Rationale explanation")
    tags: List[str] = Field(
        default_factory=list, description="Predefined competency tags"
    )
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    associated_learner_ids: List[str] = Field(
        default_factory=list,
        description=(
            "List of LearnerProfile UUIDs linked to this card (Many-to-Many)"
        ),
    )
    profile_hints: Optional[List[str]] = Field(
        None, description="Legacy alias for tags"
    )
    meeting_id: Optional[str] = Field(
        None, description="Legacy session identifier"
    )

    @model_validator(mode="after")
    def sync_tags_and_hints(self) -> "MemoryCard":
        if not self.tags and self.profile_hints:
            self.tags = list(self.profile_hints)
        elif not self.profile_hints and self.tags:
            self.profile_hints = list(self.tags)
        return self
