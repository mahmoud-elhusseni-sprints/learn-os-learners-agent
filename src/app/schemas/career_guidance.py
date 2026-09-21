"""Pydantic v2 contracts for the Task 22 Career Guidance Agent.

Recommendation categories are restricted at the schema level: anything other
than ``course``, ``task`` or ``project`` fails validation, whether it comes
from a caller, a role template, or an LLM response.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum, StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.app.schemas.models import NonEmpty

SNAKE_CASE = r"^[a-z][a-z0-9_]*$"


class RecommendationCategory(str, Enum):
    """The only recommendation types the agent may return."""

    COURSE = "course"
    TASK = "task"
    PROJECT = "project"


class CompetencyKind(StrEnum):
    TECHNICAL = "technical"
    NON_TECHNICAL = "non_technical"


class ProficiencyLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

    @property
    def rank(self) -> int:
        """1 for beginner up to 4 for expert, so levels can be compared."""
        return list(ProficiencyLevel).index(self) + 1


class Importance(StrEnum):
    CRITICAL = "critical"
    IMPORTANT = "important"


class EvidenceSource(StrEnum):
    PROJECT = "project"
    TASK = "task"
    COURSE = "course"
    ASSESSMENT = "assessment"
    REVIEW = "review"
    PRESENTATION = "presentation"
    MEETING = "meeting"
    FEEDBACK = "feedback"
    OTHER = "other"


class SignalPolarity(StrEnum):
    POSITIVE = "positive"
    CONCERN = "concern"


class EvidenceStatus(StrEnum):
    """How well the profile's evidence supports a competency."""

    DEMONSTRATED = "demonstrated"
    PARTIAL = "partially_demonstrated"
    INSUFFICIENT = "insufficient_evidence"


class GapPriority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ProfileCompleteness(StrEnum):
    EMPTY = "empty"
    LIMITED = "limited"
    SUBSTANTIAL = "substantial"


class GenerationMode(StrEnum):
    """Who wrote the recommendations in a result."""

    DETERMINISTIC = "deterministic"
    LLM = "llm"
    DETERMINISTIC_FALLBACK = "deterministic_fallback"


def normalize_title(text: str) -> str:
    """Lowercase alphanumeric words, used to spot duplicate recommendations."""
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- input ------------------------------------------------------------------


class DemonstratedSkill(_Strict):
    """A skill recorded for the learner, optionally with a level and evidence."""

    name: NonEmpty
    kind: CompetencyKind | None = None
    level: ProficiencyLevel | None = None
    evidence_ids: list[NonEmpty] = Field(default_factory=list)


class BehavioralSignal(_Strict):
    """An observed behavior, e.g. applying review feedback or missing standups."""

    signal: NonEmpty
    competency: NonEmpty | None = None
    polarity: SignalPolarity = SignalPolarity.POSITIVE
    description: str = ""
    evidence_ids: list[NonEmpty] = Field(default_factory=list)


class EvidenceItem(_Strict):
    """One piece of history: a project, review, assessment, presentation...

    ``competencies`` names what the item specifically demonstrates. ``tags``
    carries the broad taxonomy tags from ``src.app.core.tags``; tag-only
    evidence can make a competency partial but never fully demonstrated.
    """

    evidence_id: NonEmpty
    source_type: EvidenceSource
    title: NonEmpty
    summary: str = ""
    competencies: list[NonEmpty] = Field(default_factory=list)
    tags: list[NonEmpty] = Field(default_factory=list)
    outcome: NonEmpty | None = None
    occurred_at: datetime | None = None


class CareerGuidanceProfile(_Strict):
    """Everything the agent knows about the learner and their target role."""

    learner_id: NonEmpty | None = None
    target_role: NonEmpty
    skills: list[DemonstratedSkill] = Field(default_factory=list)
    behavioral_signals: list[BehavioralSignal] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def _evidence_ids_are_unique(self) -> CareerGuidanceProfile:
        ids = [item.evidence_id for item in self.evidence]
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        if duplicates:
            raise ValueError(f"Duplicate evidence_id values: {', '.join(duplicates)}")
        return self

    def known_evidence_ids(self) -> set[str]:
        """Every evidence ID the profile mentions anywhere."""
        known = {item.evidence_id for item in self.evidence}
        for skill in self.skills:
            known.update(skill.evidence_ids)
        for signal in self.behavioral_signals:
            known.update(signal.evidence_ids)
        return known


# --- role configuration -----------------------------------------------------


class ActionTemplate(_Strict):
    """Title and action text for one recommendation of a given category."""

    title: NonEmpty
    action: NonEmpty


class CompetencyRequirement(_Strict):
    """What a target role expects for one competency."""

    key: str = Field(pattern=SNAKE_CASE)
    label: NonEmpty
    kind: CompetencyKind
    importance: Importance = Importance.IMPORTANT
    required_level: ProficiencyLevel = ProficiencyLevel.INTERMEDIATE
    aliases: list[NonEmpty] = Field(default_factory=list)
    taxonomy_tags: list[NonEmpty] = Field(default_factory=list)
    course: ActionTemplate
    task: ActionTemplate


class RoleDefinition(_Strict):
    """A target career role and the competencies it expects."""

    role_id: str = Field(pattern=SNAKE_CASE)
    title: NonEmpty
    aliases: list[NonEmpty] = Field(default_factory=list)
    competencies: list[CompetencyRequirement] = Field(min_length=1)
    project: ActionTemplate

    @model_validator(mode="after")
    def _competency_keys_are_unique(self) -> RoleDefinition:
        keys = [competency.key for competency in self.competencies]
        if len(keys) != len(set(keys)):
            raise ValueError(f"Role '{self.role_id}' repeats a competency key.")
        return self


# --- output -----------------------------------------------------------------


class CompetencyAssessment(_Strict):
    """Deterministic verdict for one role competency, with its reasoning."""

    competency_key: NonEmpty
    label: NonEmpty
    kind: CompetencyKind
    importance: Importance
    required_level: ProficiencyLevel
    status: EvidenceStatus
    observed_level: ProficiencyLevel | None = None
    supporting_evidence_ids: list[NonEmpty] = Field(default_factory=list)
    concern_evidence_ids: list[NonEmpty] = Field(default_factory=list)
    rationale: NonEmpty


class SkillGap(_Strict):
    """A competency the evidence does not (yet) fully demonstrate."""

    competency_key: NonEmpty
    label: NonEmpty
    kind: CompetencyKind
    status: EvidenceStatus
    priority: GapPriority
    gap_statement: NonEmpty
    evidence_basis: NonEmpty
    related_evidence_ids: list[NonEmpty] = Field(default_factory=list)

    @field_validator("status")
    @classmethod
    def _demonstrated_is_not_a_gap(cls, value: EvidenceStatus) -> EvidenceStatus:
        if value is EvidenceStatus.DEMONSTRATED:
            raise ValueError("A demonstrated competency cannot be reported as a gap.")
        return value


class Recommendation(_Strict):
    """One actionable, evidence-grounded recommendation."""

    category: RecommendationCategory
    title: NonEmpty
    action: NonEmpty
    competencies: list[NonEmpty] = Field(min_length=1)
    gap_summary: NonEmpty
    rationale: NonEmpty
    evidence_ids: list[NonEmpty] = Field(default_factory=list)


class RecommendationSet(_Strict):
    """The envelope an LLM must return."""

    recommendations: list[Recommendation]


class CareerGuidanceResult(_Strict):
    """Final agent output: assessments, gaps and grounded recommendations."""

    learner_id: NonEmpty | None = None
    target_role: NonEmpty
    role_id: NonEmpty
    role_title: NonEmpty
    profile_completeness: ProfileCompleteness
    assessments: list[CompetencyAssessment]
    gaps: list[SkillGap]
    recommendations: list[Recommendation]
    generation_mode: GenerationMode
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _recommendations_are_grounded_and_unique(self) -> CareerGuidanceResult:
        gap_keys = {gap.competency_key for gap in self.gaps}
        seen: set[tuple[RecommendationCategory, str]] = set()
        for recommendation in self.recommendations:
            unknown = [
                key for key in recommendation.competencies if key not in gap_keys
            ]
            if unknown:
                raise ValueError(
                    f"Recommendation '{recommendation.title}' targets competencies "
                    f"that are not identified gaps: {', '.join(unknown)}"
                )
            identity = (
                recommendation.category,
                normalize_title(recommendation.title),
            )
            if identity in seen:
                raise ValueError(f"Duplicate recommendation: {recommendation.title}")
            seen.add(identity)
        return self
