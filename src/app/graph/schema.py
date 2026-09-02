"""
Professional Learner Graph - ontology and typed data models.

Sprint 1 / Task 2 deliverable for the Sprints.ai Professional Learner Graph.

This module is the single source of truth for:
  * which node types exist and what properties they carry,
  * which relationships are legal, in which direction, with what cardinality,
  * how provenance is recorded on every record,
  * and the structural rules that make the Evidence-First Principle
    impossible to violate rather than merely discouraged.

Design decisions worth knowing before you read the code
-------------------------------------------------------

1. **Evidence is a node, not an edge property.**
   One capability claim is supported by many evidence items drawn from
   different systems, each with its own provenance, strength and access
   scope.  That is a many-to-many fact and cannot live on an edge.

2. **Source facts are separated from derived assertions.**
   ``SourceNode`` subclasses mirror something that actually happened and
   always carry ``provenance``.  ``DerivedNode`` subclasses (SkillAssertion,
   Observation) are computed opinions; they carry ``computed_at`` /
   ``computed_by`` so they can be recomputed and versioned without ever
   overwriting source truth.

3. **"No evidence" is representable.**
   A SkillAssertion with ``status = NO_EVIDENCE`` is a real, storable state.
   Without this the product cannot distinguish "she cannot do X" from
   "we have not observed X yet", which is the distinction the whole product
   is built on.

4. **Ids are deterministic (UUIDv5).**
   See ``learner_graph_ids``.  Re-running ingestion produces identical ids,
   which combined with ``MERGE`` makes backfill idempotent.

5. **Four skill evidence tiers.**
   declared < exposed < assessed < demonstrated.  Employers weight these
   very differently, so they are modelled as distinct relationships rather
   than a single boolean "has skill".
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any, ClassVar, Literal, Union
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

ONTOLOGY_VERSION = "0.1.0"
SCHEMA_VERSION = "learner-graph/0.1.0"


# ===========================================================================
# Timestamp handling - ISO 8601, timezone-aware, normalised to UTC
# ===========================================================================


def _require_utc(value: datetime) -> datetime:
    """Reject naive datetimes and normalise everything to UTC.

    The source export mixes ``...+00:00`` and ``...Z`` suffixes and also
    carries a ``starts_at_local``.  Normalising on the way in means every
    recency calculation downstream compares like with like.
    """
    if value.tzinfo is None:
        raise ValueError(
            "timestamp must be timezone-aware ISO 8601 "
            "(e.g. '2026-07-21T20:33:14.676Z' or '...+00:00'); got a naive datetime"
        )
    return value.astimezone(timezone.utc)


UtcDatetime = Annotated[datetime, AfterValidator(_require_utc)]

Confidence = Annotated[float, Field(ge=0.0, le=1.0)]


# ===========================================================================
# Controlled vocabularies
#
# Values are taken from the real export wherever one already exists, so that
# ingestion (Task 3) never has to translate between two vocabularies.
# ===========================================================================


class SourceSystem(str, Enum):
    """Systems that can write into the graph."""

    LMS = "lms"
    VIRTUAL_INTERNSHIP = (
        "virtual_internship"  # lx_configs / interaction_logs / lx_turns
    )
    ASSESSMENT_ENGINE = "assessment_engine"  # grader_call results
    MEETINGS = "meetings"  # meetings.jsonl + transcripts
    MEETING_MEMORY = "meeting_memory"  # meeting_memory_cards.jsonl
    PROFILE = "profile"  # self-declared profile fields
    SCENARIO_ENGINE = "scenario_engine"  # Sprint 4 practice/validation results
    AGENT = "agent"  # agent-created recommendations


class ExtractionMethod(str, Enum):
    """How a record got into the graph - drives how much we trust it."""

    DIRECT_MAPPING = "direct_mapping"  # 1:1 field copy from a source record
    RULE_BASED = "rule_based"  # deterministic derivation
    LLM_EXTRACTION = "llm_extraction"  # Sprint 2 unstructured extraction
    HUMAN_CURATED = "human_curated"


class EvidenceType(str, Enum):
    """PRD 4.4 evidence classes."""

    DIRECT_ASSESSMENT = "direct_assessment"  # rubric / quiz / coding score
    DELIVERED_WORK = "delivered_work"  # task, project, submission, artifact
    OBSERVED_BEHAVIOR = "observed_behavior"  # meeting action, deadline handling
    MENTOR_FEEDBACK = "mentor_feedback"  # structured feedback / rubric comment
    LEARNING_EXPOSURE = "learning_exposure"  # completed module / topic
    SELF_DECLARED = "self_declared"  # "knows Python" on a profile


class EvidenceStrength(str, Enum):
    """Typical strength band from PRD 4.4.  Set per evidence item, not per type,
    because a stale or low-confidence direct assessment is not automatically
    stronger than a recent, specific delivered artifact."""

    HIGH = "high"
    MEDIUM_HIGH = "medium_high"
    MEDIUM = "medium"
    LOW = "low"


class SkillEvidenceTier(str, Enum):
    """PRD 4.3: 'Separate declared, exposed, assessed and demonstrated'."""

    DECLARED = "declared"  # learner said so
    EXPOSED = "exposed"  # completed related learning content
    ASSESSED = "assessed"  # scored against a rubric / test
    DEMONSTRATED = "demonstrated"  # shipped working artifacts


class AssertionStatus(str, Enum):
    """Evidence-strength state of a derived skill claim.

    NO_EVIDENCE exists deliberately: an assertion row saying "we looked and
    found nothing" is different from the absence of a row, and Epic 3 needs
    the former to trigger a validation scenario.
    """

    NO_EVIDENCE = "no_evidence"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class SkillCategory(str, Enum):
    """Mirrors the rubric ``scopes[].category`` values in the real export."""

    DIGITAL_AI_SKILLS = "digital_ai_skills"
    WORK_SKILLS = "work_skills"
    SOFT_SKILLS = "soft_skills"
    KNOWLEDGE_STATE = "knowledge_state"
    MISTAKE_PATTERNS = "mistake_patterns"
    DOMAIN_SPECIFIC = "domain_specific"


class LXStatus(str, Enum):
    ACTIVE = "active"
    TERMINATED = "terminated"


class LXOutcome(str, Enum):
    COMPLETED_SUCCESS = "completed_success"
    COMPLETED_FAILED = "completed_failed"
    EXPIRED = "expired"
    ABANDONED = "abandoned"


class AttemptVerdict(str, Enum):
    PASSED = "passed"
    FAILED_RETRY = "failed_retry"
    FAILED_FINAL = "failed_final"
    PENDING = "pending"


class CriterionStatus(str, Enum):
    """Per-rubric-point grader outcome as emitted in the real feedback payload."""

    YES = "Yes"
    PARTIAL = "Partial"
    NO = "No"


class MeetingKind(str, Enum):
    SPRINT_PLANNING = "sprint_planning"
    STANDUP = "standup"
    RETRO = "retro"
    AD_HOC = "ad_hoc"


class InteractionKind(str, Enum):
    LEARNER_MESSAGE = "learner_message"
    ACTOR_RESPONSE = "actor_response"
    HUMAN_MENTOR_MESSAGE = "human_mentor_message"
    TASK_KICKOFF = "task_kickoff"
    DAILY_CHECK = "daily_check"
    SUBMISSION = "learner_submission"
    FEEDBACK_DELIVERED = "feedback_delivered"
    DEADLINE_REMINDER = "deadline_reminder"
    MISROUTED_REDIRECT = "misrouted_redirect"
    SCENARIO_EVENT = "scenario_event"
    OTHER = "other"


class ObservationCategory(str, Enum):
    """Behavioural observation buckets, aligned with the memory-card metric keys.

    Deliberately describes *situations*, not personality types.
    """

    COLLABORATION = "collaboration"
    PROBLEM_SOLVING = "problem_solving"
    DEADLINE_HANDLING = "deadline_handling"
    COMMUNICATION = "communication"
    INITIATIVE = "initiative"
    ADAPTABILITY = "adaptability"
    HELP_SEEKING = "help_seeking"


class IdentityResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    CONFLICT = "conflict"


class CareerGoalStatus(str, Enum):
    STATED = "stated"
    UNKNOWN = "unknown"  # FR-11 requires an explicit unknown state


class GapType(str, Enum):
    SKILL_GAP = "skill_gap"
    EVIDENCE_GAP = "evidence_gap"
    BEHAVIORAL_EVIDENCE_GAP = "behavioral_evidence_gap"
    RECENCY_GAP = "recency_gap"
    CAREER_GOAL_GAP = "career_goal_gap"


class RecommendationStatus(str, Enum):
    RECOMMENDED = "recommended"
    APPROVED = "approved"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    EVALUATED = "evaluated"
    EVIDENCE_INGESTED = "evidence_ingested"


class AccessScope(str, Enum):
    """Coarse visibility band stamped on every Evidence item (FR-03).

    Enforcement lands in Sprint 2, but the field has to exist now or that
    sprint starts with a migration.
    """

    INTERNAL_ONLY = "internal_only"  # Sprints staff only
    EMPLOYER_SHAREABLE = "employer_shareable"
    LEARNER_VISIBLE = "learner_visible"
    RESTRICTED = "restricted"  # never leaves the platform


# ===========================================================================
# Base models
# ===========================================================================


class GraphModel(BaseModel):
    """Shared config.  ``extra='forbid'`` is deliberate: a typo in an ingestion
    script should fail loudly at write time rather than silently create an
    orphan property in Neo4j."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
        use_enum_values=False,
    )


class Provenance(GraphModel):
    """Where a record came from.  Attached to every source-derived node.

    ``observed_at`` is when the thing happened in the real world;
    ``ingested_at`` is when we wrote it down.  They are different and the
    recency logic in Epic 2/3 needs the former.
    """

    source_system: SourceSystem
    source_id: str = Field(min_length=1, description="Primary key in the source system")
    source_type: str = Field(min_length=1, description="Record type, e.g. 'lx_config'")
    source_locator: str | None = Field(
        default=None,
        description=(
            "Sub-record pointer, e.g. 'turn:545', 'rubric_point:101', "
            "'entry_index:12'"
        ),
    )
    source_url: str | None = None
    observed_at: UtcDatetime
    ingested_at: UtcDatetime
    evidence_type: "EvidenceType | None" = Field(
        default=None,
        description=(
            "Evidence class this record supports. Required on Evidence "
            "provenance and auto-filled from the node; left None on "
            "structural nodes (Learner, Round, Task...) which are not "
            "themselves evidence."
        ),
    )
    extraction_method: ExtractionMethod = ExtractionMethod.DIRECT_MAPPING
    extractor_version: str = Field(default=f"ontology@{ONTOLOGY_VERSION}")


class EvidenceProvenance(Provenance):
    """Provenance for a record that IS evidence.

    The specification defines the provenance tuple as
    ``(source_system, source_id, timestamp, evidence_type)``. On the base
    ``Provenance`` the last element is optional, because structural records
    such as a Learner or a Round carry provenance without being evidence
    themselves.

    Here it is **required**, so the complete tuple is enforced by the type
    system rather than by a convention. ``Evidence.provenance`` is declared
    as this type, which means an Evidence node whose provenance omits
    ``evidence_type`` cannot be constructed at all.
    """

    evidence_type: EvidenceType = Field(
        description="Evidence class this record supports. Required here."
    )


class GraphNode(GraphModel):
    """Every node has a UUID primary key and a creation timestamp."""

    id: UUID
    created_at: UtcDatetime
    updated_at: UtcDatetime | None = None


class SourceNode(GraphNode):
    """A node that mirrors something that actually happened in a source system."""

    provenance: Provenance


class DerivedNode(GraphNode):
    """A computed opinion.  Never overwrites source truth; always versioned."""

    computed_at: UtcDatetime
    computed_by: str = Field(
        min_length=1,
        description="Versioned producer, e.g. 'skill-aggregator@0.1.0'",
    )
    derivation_note: str | None = None


# ===========================================================================
# Node types - organisational scope
# ===========================================================================


class Cohort(SourceNode):
    """A programme intake, e.g. 'sprints-2026-spring'."""

    label: Literal["Cohort"] = "Cohort"
    cohort_key: str
    name: str
    start_date: UtcDatetime | None = None
    end_date: UtcDatetime | None = None
    duration_weeks: int | None = Field(default=None, ge=1)
    organization_id: str | None = None


class Round(SourceNode):
    """An internship round, e.g. 'round2'.  Employer authorisation is scoped
    at this level (FR-05), which is why it must be a first-class node."""

    label: Literal["Round"] = "Round"
    round_key: str
    name: str


class Group(SourceNode):
    """A track/group inside a round, e.g. 'G2 - AI Engineer Internship'."""

    label: Literal["Group"] = "Group"
    group_key: str
    name: str
    track: str | None = Field(default=None, description="e.g. 'AI Engineer'")


# ===========================================================================
# Node types - identity
# ===========================================================================


class Learner(SourceNode):
    """The canonical person.  One Learner node per real human, however many
    source identities point at them."""

    label: Literal["Learner"] = "Learner"
    canonical_email: str
    display_name: str
    timezone: str | None = None
    learner_status: str | None = None

    sensitive_attributes: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Optional profile context (location, education level, field of study). "
            "PRD 8.2: these are NEVER inputs to talent ranking or matching. "
            "Kept off the top level so they cannot be picked up accidentally."
        ),
    )

    #: Consumed by the Sprint 3 ranking service as a hard exclusion list.
    RANKING_EXCLUDED_FIELDS: ClassVar[tuple[str, ...]] = (
        "sensitive_attributes",
        "canonical_email",
        "display_name",
        "timezone",
    )

    @field_validator("canonical_email")
    @classmethod
    def _looks_like_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError(f"canonical_email must contain '@': {v!r}")
        return v.lower()


class LearnerIdentity(SourceNode):
    """One source-system identity that maps onto a canonical Learner.

    Task 4 (identity resolution) owns this node.  Modelling it explicitly is
    what lets US-01 ("all source IDs resolved to one canonical profile") be
    satisfied *without losing the source mappings*, and gives the unresolved
    queue somewhere to live.
    """

    label: Literal["LearnerIdentity"] = "LearnerIdentity"
    source_learner_id: str
    source_email: str | None = None
    source_display_name: str | None = None
    resolution_status: IdentityResolutionStatus = IdentityResolutionStatus.RESOLVED
    resolution_method: str | None = Field(
        default=None, description="e.g. 'exact_email', 'manual_merge'"
    )
    resolved_at: UtcDatetime | None = None
    merge_note: str | None = None


# ===========================================================================
# Node types - skills
# ===========================================================================


class Skill(GraphNode):
    """A canonical skill.  Not a SourceNode: skills are registry entries owned
    by the taxonomy, not records copied from one system.  Aliases collapse the
    many surface forms ('Python 3.11', 'python', 'Python') onto one node."""

    label: Literal["Skill"] = "Skill"
    canonical_name: str = Field(min_length=1)
    slug: str = Field(min_length=1)
    category: SkillCategory
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None
    taxonomy_version: str = "skills@0.1.0"

    @field_validator("aliases")
    @classmethod
    def _dedupe_aliases(cls, v: list[str]) -> list[str]:
        return sorted({a.strip().lower() for a in v if a.strip()})


# ===========================================================================
# Node types - work and learning
# ===========================================================================


class Task(SourceNode):
    """The reusable specification of a task.

    Distinct from LearningExperience: in the real export one
    ``task_definition_id`` is handed to several learners.  Collapsing the two
    would destroy the difference between 'the task' and 'her attempt at it'.
    """

    label: Literal["Task"] = "Task"
    task_key: str
    headline: str
    description: str | None = None
    task_archetype: str | None = Field(
        default=None, description="e.g. 'single_submission'"
    )
    technologies: list[str] = Field(default_factory=list)
    deliverable_format: str | None = None
    functional_requirements: list[str] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)
    sprint_label: str | None = None


class Project(SourceNode):
    """A body of work several tasks contribute to."""

    label: Literal["Project"] = "Project"
    project_key: str
    name: str
    description: str | None = None
    repository_url: str | None = None


class LearningExperience(SourceNode):
    """One task instance assigned to one learner (an 'LX' in the source data)."""

    label: Literal["LearningExperience"] = "LearningExperience"
    lx_key: str
    flow_id: str | None = None
    task_archetype_id: str | None = None
    status: LXStatus
    outcome: LXOutcome | None = None
    trial_count: int = Field(default=0, ge=0)
    extension_used: bool = False
    activated_at: UtcDatetime | None = None
    deadline_at: UtcDatetime | None = None
    terminated_at: UtcDatetime | None = None
    terminated_reason: str | None = None
    scenario_key: str | None = None
    revision: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _terminated_needs_reason_or_outcome(self) -> "LearningExperience":
        if (
            self.status is LXStatus.TERMINATED
            and self.outcome is None
            and not self.terminated_reason
        ):
            # Not fatal - the real export has 17 rows like this - but we record
            # that the outcome is genuinely unknown rather than pretending.
            object.__setattr__(
                self, "terminated_reason", "outcome not recorded in source"
            )
        return self


class Attempt(SourceNode):
    """One graded attempt at an LX.  ``trial_count`` in the source data and the
    ``attempt_failed_retry`` / ``attempt_passed`` tags make this a real entity:
    Learner A4's LX 144bd399 has three attempts with different verdicts."""

    label: Literal["Attempt"] = "Attempt"
    attempt_number: int = Field(ge=1)
    verdict: AttemptVerdict
    submitted_at: UtcDatetime | None = None
    evaluated_at: UtcDatetime | None = None


class Submission(SourceNode):
    """What the learner handed in for one attempt at a task.

    Mirrors ``entry.submission`` in the interaction log. A submission is the
    unit an assessment is run against, and the container for the artifacts a
    grader cites, so it is the join point between "work delivered" and
    "work evaluated".
    """

    label: Literal["Submission"] = "Submission"
    kind: str = Field(description="e.g. 'attachments', 'text', 'link'")
    text: str | None = Field(
        default=None, description="Free-text body or the pasted link"
    )
    attachment_count: int = Field(default=0, ge=0)
    attachment_names: list[str] = Field(
        default_factory=list, description="Filenames as reported by the source"
    )
    submission_url: str | None = Field(
        default=None, description="Repository, PR or branch URL when one was given"
    )
    submitted_at: UtcDatetime | None = Field(
        default=None, description="When the learner handed it in"
    )
    is_resubmission: bool = Field(
        default=False, description="True when a previous attempt already existed"
    )
    artifact_count: int = Field(
        default=0, ge=0, description="Artifacts extracted from this submission"
    )

    @model_validator(mode="after")
    def _url_implies_link(self) -> "Submission":
        if self.submission_url and not self.submission_url.startswith(
            ("http://", "https://")
        ):
            raise ValueError(
                f"submission_url must be an absolute URL, got {self.submission_url!r}"
            )
        return self


class Artifact(SourceNode):
    """A concrete file/chunk inside a submission.

    The grader cites these by id (``'backend/app/services/script_agent.py_0'``),
    so they are the finest-grained provenance anchor available and make
    'show me the evidence' land on an actual line of work.
    """

    label: Literal["Artifact"] = "Artifact"
    artifact_key: str
    path: str | None = None
    artifact_type: str | None = Field(
        default=None, description="e.g. 'code', 'readme', 'diff'"
    )
    content_excerpt: str | None = Field(default=None, max_length=4000)


# ===========================================================================
# Node types - assessment
# ===========================================================================


class Rubric(SourceNode):
    label: Literal["Rubric"] = "Rubric"
    rubric_key: str
    version: str = "1"
    criterion_count: int = Field(default=0, ge=0)


class RubricCriterion(SourceNode):
    """One scope/point pair from the task rubric.  This is where a skill gets
    attached to an assessable requirement, so it is the hinge between
    'work delivered' and 'skill demonstrated'."""

    label: Literal["RubricCriterion"] = "RubricCriterion"
    criterion_key: str
    scope_id: int | None = None
    point_id: int | None = None
    category: str | None = None
    polarity: str | None = Field(default=None, description="'positive' or 'negative'")
    requirement: str | None = None
    description: str | None = None
    evaluation_criteria: str | None = None


class Assessment(SourceNode):
    """One evaluation event - a grader call, quiz submission or coding test."""

    label: Literal["Assessment"] = "Assessment"
    assessment_kind: str = Field(
        description="e.g. 'grader_call', 'quiz', 'coding_challenge'"
    )
    verdict: str | None = Field(
        default=None, description="Source verdict, e.g. 'passed', 'failed_retry'"
    )
    summary: str | None = Field(
        default=None, description="Grader's overall summary of the submission"
    )
    mentor_reply: str | None = Field(
        default=None, description="Feedback text actually delivered to the learner"
    )
    score: float | None = Field(default=None, ge=0)
    max_score: float | None = Field(default=None, ge=0)
    criteria_total: int = Field(
        default=0, ge=0, description="Rubric points the grader evaluated"
    )
    criteria_met: int = Field(default=0, ge=0, description="Points scored 'Yes'")
    criteria_partial: int = Field(
        default=0, ge=0, description="Points scored 'Partial'"
    )
    criteria_unmet: int = Field(default=0, ge=0, description="Points scored 'No'")
    grader_version: str | None = None
    evaluated_at: UtcDatetime | None = None

    @model_validator(mode="after")
    def _score_within_max(self) -> "Assessment":
        if (
            self.score is not None
            and self.max_score is not None
            and self.score > self.max_score
        ):
            raise ValueError(f"score {self.score} exceeds max_score {self.max_score}")
        breakdown = self.criteria_met + self.criteria_partial + self.criteria_unmet
        if self.criteria_total and breakdown > self.criteria_total:
            raise ValueError(
                f"criteria breakdown ({breakdown}) exceeds "
                f"criteria_total ({self.criteria_total})"
            )
        return self


# ===========================================================================
# Node types - meetings and interactions
# ===========================================================================


class Meeting(SourceNode):
    """A scheduled session - standup, sprint planning, retro or ad-hoc.

    Meetings are the origin of behavioural evidence, so the extraction fields
    matter: an un-transcribed meeting must not silently look like a meeting
    with nothing in it.
    """

    label: Literal["Meeting"] = "Meeting"
    meeting_key: str
    kind: MeetingKind
    topic: str | None = None
    starts_at_utc: UtcDatetime | None = None
    starts_at_local: str | None = Field(
        default=None,
        description="Source-local start string, kept verbatim; never used for "
        "recency maths - use starts_at_utc for that.",
    )
    duration_min: int | None = Field(default=None, ge=0)
    zoom_meeting_id: str | None = None
    zoom_meeting_uuid: str | None = None
    attendee_count: int | None = Field(default=None, ge=0)
    transcript_available: bool = Field(
        default=False, description="A transcript exists and was parsed"
    )
    extraction_status: str | None = Field(
        default=None, description="e.g. 'pending', 'done', 'failed'"
    )
    extracted_at: UtcDatetime | None = None
    last_extraction_error: str | None = None


class Interaction(SourceNode):
    """One entry from the interaction log - a chat exchange, kickoff brief,
    daily check-in, redirect, etc.  Covers the brief's 'Interaction/Chat'."""

    label: Literal["Interaction"] = "Interaction"
    interaction_kind: InteractionKind
    tags: list[str] = Field(
        default_factory=list, description="Raw source tags, kept verbatim"
    )
    summary: str | None = None
    trigger_node_id: str | None = Field(
        default=None, description="Orchestrator node that fired this, e.g. n8n"
    )
    occurred_at: UtcDatetime
    entry_index: int | None = Field(
        default=None,
        ge=0,
        description="Position within the source log, for stable ordering",
    )
    message_count: int = Field(default=0, ge=0)
    participant_roles: list[str] = Field(
        default_factory=list, description="e.g. ['learner', 'mentor']"
    )
    initiated_by: str | None = Field(
        default=None, description="'learner', 'mentor', 'manager' or 'system'"
    )
    carries_submission: bool = Field(
        default=False, description="This entry contained a learner submission"
    )
    carries_feedback: bool = Field(
        default=False, description="This entry contained grader or mentor feedback"
    )
    struggle_area: str | None = None
    struggle_resolved: bool | None = None


# ===========================================================================
# Node type - Evidence (the centre of the ontology)
# ===========================================================================


class Evidence(SourceNode):
    """An atomic, citable piece of proof about a learner.

    Every Evidence node must point back at the record it came from
    (``DERIVED_FROM``) and at the learner it concerns
    (``EVIDENCE_FOR_LEARNER``).  Both are enforced structurally by
    ``LearnerGraph`` rather than left to convention.
    """

    label: Literal["Evidence"] = "Evidence"
    provenance: EvidenceProvenance = Field(
        description=(
            "Stricter than the base Provenance: evidence_type is required, so "
            "the full (source_system, source_id, timestamp, evidence_type) "
            "tuple is enforced by the type itself."
        )
    )
    evidence_type: EvidenceType
    strength: EvidenceStrength
    confidence: Confidence = 1.0
    title: str = Field(min_length=1)
    content: str = Field(
        min_length=1,
        description=(
            "The quotable substance - grader reason, feedback line, meeting " "excerpt."
        ),
    )
    observed_at: UtcDatetime = Field(
        description="When the evidenced behaviour occurred (drives recency weighting)."
    )
    access_scope: AccessScope = AccessScope.INTERNAL_ONLY
    criterion_status: CriterionStatus | None = Field(
        default=None,
        description="Set when the evidence came from a graded rubric point.",
    )

    @model_validator(mode="after")
    def _provenance_carries_evidence_type(self) -> "Evidence":
        """Mirror ``evidence_type`` onto the provenance record.

        The brief specifies provenance as
        ``(source_system, source_id, timestamp, evidence_type)``. Keeping the
        authoritative value on the node and copying it down means the full
        tuple is present wherever provenance is read - including after
        ``flatten_node`` writes it to Neo4j - without the two being able to
        drift apart.
        """
        prov = self.provenance
        if prov.evidence_type is not self.evidence_type:
            raise ValueError(
                f"provenance.evidence_type ({prov.evidence_type.value}) "
                f"contradicts Evidence.evidence_type ({self.evidence_type.value})"
            )
        return self


# ===========================================================================
# Node types - derived
# ===========================================================================

_BANNED_TRAIT_WORDS = {
    "lazy",
    "stupid",
    "difficult",
    "toxic",
    "unmotivated",
    "incompetent",
    "arrogant",
    "slow learner",
    "bad attitude",
    "careless",
}


class Observation(DerivedNode):
    """A contextual behavioural observation.

    PRD 4.3 / 8.2: store *event + behaviour + outcome + source + confidence*,
    never a personality label.  The validator below is a guardrail that makes
    the policy enforceable in code instead of a line in a doc.
    """

    label: Literal["Observation"] = "Observation"
    category: ObservationCategory
    context: str = Field(
        min_length=1, description="The situation, e.g. 'company API went down mid-task'"
    )
    behavior: str = Field(min_length=1, description="What the learner did, observably")
    outcome: str | None = Field(default=None, description="What resulted")
    observed_at: UtcDatetime
    confidence: Confidence = 0.5

    @model_validator(mode="after")
    def _no_personality_labels(self) -> "Observation":
        blob = " ".join(
            filter(None, [self.context, self.behavior, self.outcome or ""])
        ).lower()
        hits = sorted(w for w in _BANNED_TRAIT_WORDS if w in blob)
        if hits:
            raise ValueError(
                "Observation reads as a personality label, which PRD 8.2 forbids. "
                f"Offending term(s): {hits}. Describe the event and the observable "
                "behaviour instead (e.g. 'missed two of three sprint deadlines')."
            )
        return self


class SkillAssertion(DerivedNode):
    """The derived, evidence-backed state of one learner-skill-tier triple.

    This node is the reason the product can answer "we don't know" honestly:
    ``status = NO_EVIDENCE`` is storable, queryable and actionable, and it is
    what Epic 3 turns into a validation scenario.
    """

    label: Literal["SkillAssertion"] = "SkillAssertion"
    tier: SkillEvidenceTier
    status: AssertionStatus
    confidence: Confidence = 0.0
    evidence_count: int = Field(default=0, ge=0)
    evidence_source_count: int = Field(
        default=0,
        ge=0,
        description="Distinct source_systems behind this assertion - the "
        "diversity signal that stops one chatty source dominating.",
    )
    first_evidence_at: UtcDatetime | None = None
    latest_evidence_at: UtcDatetime | None = None
    rationale: str | None = None

    @model_validator(mode="after")
    def _status_matches_evidence(self) -> "SkillAssertion":
        if self.status is AssertionStatus.NO_EVIDENCE and self.evidence_count > 0:
            raise ValueError(
                f"status=no_evidence contradicts evidence_count={self.evidence_count}"
            )
        if self.status is not AssertionStatus.NO_EVIDENCE and self.evidence_count == 0:
            raise ValueError(
                f"status={self.status.value} requires at least one evidence item; "
                "use status=no_evidence when nothing was found"
            )
        if (
            self.first_evidence_at
            and self.latest_evidence_at
            and self.first_evidence_at > self.latest_evidence_at
        ):
            raise ValueError("first_evidence_at is later than latest_evidence_at")
        return self


# ===========================================================================
# Node types - career goal and the Sprint 4 closed loop
# ===========================================================================


class CareerGoal(SourceNode):
    """FR-11 (P0): every pilot learner has a goal or an explicit unknown state."""

    label: Literal["CareerGoal"] = "CareerGoal"
    status: CareerGoalStatus
    target_role: str | None = None
    stated_at: UtcDatetime | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _stated_needs_role(self) -> "CareerGoal":
        if self.status is CareerGoalStatus.STATED and not self.target_role:
            raise ValueError(
                "status='stated' requires target_role; use status='unknown' otherwise"
            )
        if self.status is CareerGoalStatus.UNKNOWN and self.target_role:
            raise ValueError("status='unknown' must not carry a target_role")
        return self


class Scenario(SourceNode):
    """Approved practice/validation scenario (Sprint 4 catalog).

    Included now as a stub so Sprint 4 extends the ontology instead of
    migrating it.
    """

    label: Literal["Scenario"] = "Scenario"
    scenario_key: str
    title: str
    description: str | None = None
    difficulty: str | None = None
    estimated_minutes: int | None = Field(default=None, ge=1)
    task_type: str | None = None
    version: str = "1"
    approved: bool = False


class Recommendation(DerivedNode):
    """A gap-driven recommendation (Sprint 4 stub)."""

    label: Literal["Recommendation"] = "Recommendation"
    gap_type: GapType
    reason: str = Field(
        min_length=1, description="The profile signal that triggered this"
    )
    priority: int = Field(ge=1, le=5)
    status: RecommendationStatus = RecommendationStatus.RECOMMENDED
    expected_evidence: str | None = None


# ===========================================================================
# Node types - employer access (Sprint 2 stubs, fields needed now)
# ===========================================================================


class Employer(SourceNode):
    label: Literal["Employer"] = "Employer"
    employer_key: str
    name: str


class AccessGrant(SourceNode):
    """Deny-by-default authorisation record (FR-05)."""

    label: Literal["AccessGrant"] = "AccessGrant"
    grant_key: str
    granted_at: UtcDatetime
    expires_at: UtcDatetime | None = None
    allowed_evidence_types: list[EvidenceType] = Field(default_factory=list)
    allowed_access_scopes: list[AccessScope] = Field(
        default_factory=lambda: [AccessScope.EMPLOYER_SHAREABLE]
    )


# ===========================================================================
# Discriminated union of every node type
# ===========================================================================

AnyNode = Annotated[
    Union[
        Cohort,
        Round,
        Group,
        Learner,
        LearnerIdentity,
        Skill,
        Task,
        Project,
        LearningExperience,
        Attempt,
        Submission,
        Artifact,
        Rubric,
        RubricCriterion,
        Assessment,
        Meeting,
        Interaction,
        Evidence,
        Observation,
        SkillAssertion,
        CareerGoal,
        Scenario,
        Recommendation,
        Employer,
        AccessGrant,
    ],
    Field(discriminator="label"),
]

NODE_CLASSES: dict[str, type[GraphNode]] = {
    cls.model_fields["label"].default: cls
    for cls in (
        Cohort,
        Round,
        Group,
        Learner,
        LearnerIdentity,
        Skill,
        Task,
        Project,
        LearningExperience,
        Attempt,
        Submission,
        Artifact,
        Rubric,
        RubricCriterion,
        Assessment,
        Meeting,
        Interaction,
        Evidence,
        Observation,
        SkillAssertion,
        CareerGoal,
        Scenario,
        Recommendation,
        Employer,
        AccessGrant,
    )
}


# ===========================================================================
# Edges
# ===========================================================================


class EdgeType(str, Enum):
    # identity + scope
    IDENTIFIES = "IDENTIFIES"
    MEMBER_OF = "MEMBER_OF"
    PART_OF_ROUND = "PART_OF_ROUND"
    PART_OF_COHORT = "PART_OF_COHORT"

    # work and learning
    HAS_LEARNING_EXPERIENCE = "HAS_LEARNING_EXPERIENCE"
    INSTANCE_OF = "INSTANCE_OF"
    COMPLETED_TASK = "COMPLETED_TASK"
    PART_OF_PROJECT = "PART_OF_PROJECT"
    HAS_ATTEMPT = "HAS_ATTEMPT"
    SUBMITTED = "SUBMITTED"
    SUBMITTED_IN = "SUBMITTED_IN"
    CONTAINS_ARTIFACT = "CONTAINS_ARTIFACT"

    # assessment
    HAS_RUBRIC = "HAS_RUBRIC"
    HAS_CRITERION = "HAS_CRITERION"
    EVALUATED_BY = "EVALUATED_BY"
    USED_RUBRIC = "USED_RUBRIC"
    SCORED_CRITERION = "SCORED_CRITERION"
    TARGETS_SKILL = "TARGETS_SKILL"
    REQUIRES_SKILL = "REQUIRES_SKILL"

    # meetings / interactions
    PARTICIPATED_IN = "PARTICIPATED_IN"
    HELD_FOR_GROUP = "HELD_FOR_GROUP"
    OCCURRED_IN = "OCCURRED_IN"

    # evidence spine
    EVIDENCE_FOR_LEARNER = "EVIDENCE_FOR_LEARNER"
    DERIVED_FROM = "DERIVED_FROM"
    SUPPORTED_BY_EVIDENCE = "SUPPORTED_BY_EVIDENCE"
    EVIDENCE_ABOUT_SKILL = "EVIDENCE_ABOUT_SKILL"

    # derived skill state
    HAS_SKILL_ASSERTION = "HAS_SKILL_ASSERTION"
    ABOUT_SKILL = "ABOUT_SKILL"
    DECLARED_SKILL = "DECLARED_SKILL"
    EXPOSED_TO_SKILL = "EXPOSED_TO_SKILL"
    ASSESSED_ON_SKILL = "ASSESSED_ON_SKILL"
    DEMONSTRATED_SKILL = "DEMONSTRATED_SKILL"

    # behaviour
    HAS_OBSERVATION = "HAS_OBSERVATION"
    OBSERVED_IN = "OBSERVED_IN"

    # career / closed loop
    HAS_CAREER_GOAL = "HAS_CAREER_GOAL"
    GOAL_TARGETS_SKILL = "GOAL_TARGETS_SKILL"
    RECOMMENDED_FOR = "RECOMMENDED_FOR"
    RECOMMENDS_SCENARIO = "RECOMMENDS_SCENARIO"
    ADDRESSES_GAP_IN = "ADDRESSES_GAP_IN"
    VALIDATES_SKILL = "VALIDATES_SKILL"

    # access
    HAS_ACCESS_GRANT = "HAS_ACCESS_GRANT"
    GRANTS_ACCESS_TO = "GRANTS_ACCESS_TO"


class Cardinality(str, Enum):
    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"  # one source -> many targets, each target has one source
    MANY_TO_ONE = "N:1"  # many sources -> one target, each source has one target
    MANY_TO_MANY = "N:M"


# ---- typed edge property payloads -----------------------------------------


class MembershipProps(GraphModel):
    role: str = "member"
    added_at: UtcDatetime | None = None


class CompletedTaskProps(GraphModel):
    """Denormalised summary of how a learner finished a task definition."""

    lx_key: str
    outcome: LXOutcome | None = None
    completed_at: UtcDatetime | None = None
    attempts: int = Field(default=1, ge=1)


class ParticipationProps(GraphModel):
    attendance: str = Field(
        default="attended", description="'attended' | 'absent' | 'partial'"
    )
    role: str = "participant"


class SkillTierProps(GraphModel):
    """Carried on the four denormalised learner->skill convenience edges.

    These edges exist for fast Cypher in Epic 2/3; the SkillAssertion node
    remains the authoritative, versioned record.
    """

    assertion_id: UUID
    status: AssertionStatus
    confidence: Confidence = 0.0
    evidence_count: int = Field(default=0, ge=0)
    latest_evidence_at: UtcDatetime | None = None


class SubmissionProps(GraphModel):
    """Carried on ``(:Learner)-[:SUBMITTED]->(:Submission)``."""

    submitted_at: UtcDatetime | None = None
    attempt_number: int = Field(default=1, ge=1)
    is_resubmission: bool = False


class SubmittedInProps(GraphModel):
    """Carried on ``(:Submission)-[:SUBMITTED_IN]->(:Attempt)``."""

    attempt_number: int = Field(default=1, ge=1)
    is_final_attempt: bool = False


class ArtifactCitationProps(GraphModel):
    """Carried on ``(:Submission)-[:CONTAINS_ARTIFACT]->(:Artifact)``.

    ``cited_by_grader`` distinguishes a file the grader actually pointed at
    from one that merely existed in the submission - a much stronger signal
    when an employer asks to see the evidence.
    """

    cited_by_grader: bool = False
    citation_count: int = Field(default=0, ge=0)
    chunk_index: int | None = Field(default=None, ge=0)


class EvaluationProps(GraphModel):
    """Carried on ``(:Attempt)-[:EVALUATED_BY]->(:Assessment)``."""

    evaluated_at: UtcDatetime | None = None
    verdict: AttemptVerdict | None = None
    is_final_evaluation: bool = False


class RubricUseProps(GraphModel):
    """Carried on ``(:Assessment)-[:USED_RUBRIC]->(:Rubric)``."""

    rubric_version: str = "1"
    criteria_evaluated: int = Field(default=0, ge=0)


class MeetingScopeProps(GraphModel):
    """Carried on ``(:Meeting)-[:HELD_FOR_GROUP]->(:Group)``."""

    round_key: str | None = None
    recurring: bool = False


class OccurredInProps(GraphModel):
    """Carried on ``(:Interaction)-[:OCCURRED_IN]->(:LearningExperience)``."""

    sequence_index: int | None = Field(default=None, ge=0)
    days_into_lx: int | None = Field(default=None, ge=0)


class ProjectMembershipProps(GraphModel):
    """Carried on ``(:Task)-[:PART_OF_PROJECT]->(:Project)``.

    A project is delivered in ordered stages across sprints, and the same
    project spans several tasks. Recording the sprint and order on the edge
    lets a timeline be reconstructed without inferring it from dates.
    """

    sprint_label: str | None = Field(
        default=None, description="e.g. 'week 3', 'Sprint 4'"
    )
    sequence: int | None = Field(
        default=None, ge=0, description="Order of this task within the project"
    )
    is_primary_deliverable: bool = False


class DerivedFromProps(GraphModel):
    """Carried on every ``(:Evidence)-[:DERIVED_FROM]->(...)`` edge.

    This edge is the traceability link, so it carries the **full provenance
    tuple required by the specification** -
    ``(source_system, source_id, timestamp, evidence_type)`` - as required
    fields, not optional ones.

    Duplicating the tuple from the Evidence node is deliberate. In Neo4j the
    edge can then be filtered directly ("show me every high-confidence link
    derived from the assessment engine in July") without touching the node.
    ``LearnerGraph._provenance_tuple_consistent`` rejects any edge whose copy
    disagrees with its Evidence node, so the two cannot drift apart.

    ``source_locator`` and ``excerpt`` are the edge's own contribution: the
    pointer into the specific part of the source record - which transcript
    turn, which rubric point, which chunk of a file.
    """

    source_system: SourceSystem = Field(
        description="Which system the evidence came from (tuple element 1)"
    )
    source_id: str = Field(
        min_length=1, description="Primary key in that system (tuple element 2)"
    )
    observed_at: UtcDatetime = Field(
        description="When the evidenced thing happened (tuple element 3)"
    )
    evidence_type: EvidenceType = Field(
        description="Class of evidence this link supports (tuple element 4)"
    )
    source_locator: str | None = Field(
        default=None, description="e.g. 'turn:657', 'rubric_point:102'"
    )
    excerpt: str | None = Field(
        default=None,
        max_length=1000,
        description="The quoted span this evidence was drawn from",
    )
    extraction_confidence: Confidence = 1.0


class ObservedInProps(GraphModel):
    """Carried on ``(:Observation)-[:OBSERVED_IN]->(...)``."""

    source_locator: str | None = None
    excerpt: str | None = Field(default=None, max_length=1000)


class ScoredCriterionProps(GraphModel):
    """The grader's per-rubric-point result, kept at full fidelity."""

    status: CriterionStatus
    confidence: Confidence
    reason: str | None = None
    artifact_keys: list[str] = Field(default_factory=list)


class EdgeSpec(GraphModel):
    """One legal relationship: direction, endpoints, cardinality, payload."""

    type: EdgeType
    source_label: str
    target_label: str
    cardinality: Cardinality
    description: str
    property_model: str | None = None  # name of a GraphModel above


#: The authoritative relationship registry.  Anything not listed here is
#: rejected at validation time, which is what stops Task 3 and Task 5 from
#: quietly inventing divergent edges.
EDGE_SPECS: tuple[EdgeSpec, ...] = (
    # --- identity + organisational scope ---
    EdgeSpec(
        type=EdgeType.IDENTIFIES,
        source_label="LearnerIdentity",
        target_label="Learner",
        cardinality=Cardinality.MANY_TO_ONE,
        description="A source-system identity resolves to one canonical learner.",
    ),
    EdgeSpec(
        type=EdgeType.MEMBER_OF,
        source_label="Learner",
        target_label="Group",
        cardinality=Cardinality.MANY_TO_MANY,
        description="Learner belongs to a track/group.",
        property_model="MembershipProps",
    ),
    EdgeSpec(
        type=EdgeType.PART_OF_ROUND,
        source_label="Group",
        target_label="Round",
        cardinality=Cardinality.MANY_TO_ONE,
        description="Group sits inside a round.",
    ),
    EdgeSpec(
        type=EdgeType.PART_OF_COHORT,
        source_label="Round",
        target_label="Cohort",
        cardinality=Cardinality.MANY_TO_ONE,
        description="Round belongs to a cohort.",
    ),
    # --- work and learning ---
    EdgeSpec(
        type=EdgeType.HAS_LEARNING_EXPERIENCE,
        source_label="Learner",
        target_label="LearningExperience",
        cardinality=Cardinality.ONE_TO_MANY,
        description="A task instance assigned to this learner.",
    ),
    EdgeSpec(
        type=EdgeType.INSTANCE_OF,
        source_label="LearningExperience",
        target_label="Task",
        cardinality=Cardinality.MANY_TO_ONE,
        description="Which task specification this instance realises.",
    ),
    EdgeSpec(
        type=EdgeType.COMPLETED_TASK,
        source_label="Learner",
        target_label="Task",
        cardinality=Cardinality.MANY_TO_MANY,
        description="Denormalised completion edge for fast history queries.",
        property_model="CompletedTaskProps",
    ),
    EdgeSpec(
        type=EdgeType.PART_OF_PROJECT,
        source_label="Task",
        target_label="Project",
        cardinality=Cardinality.MANY_TO_ONE,
        description="Task contributes to a project.",
        property_model="ProjectMembershipProps",
    ),
    EdgeSpec(
        type=EdgeType.HAS_ATTEMPT,
        source_label="LearningExperience",
        target_label="Attempt",
        cardinality=Cardinality.ONE_TO_MANY,
        description="Graded attempts, in order.",
    ),
    EdgeSpec(
        type=EdgeType.SUBMITTED,
        source_label="Learner",
        target_label="Submission",
        cardinality=Cardinality.ONE_TO_MANY,
        description="Learner handed this in.",
        property_model="SubmissionProps",
    ),
    EdgeSpec(
        type=EdgeType.SUBMITTED_IN,
        source_label="Submission",
        target_label="Attempt",
        cardinality=Cardinality.MANY_TO_ONE,
        description="Submission belongs to an attempt.",
        property_model="SubmittedInProps",
    ),
    EdgeSpec(
        type=EdgeType.CONTAINS_ARTIFACT,
        source_label="Submission",
        target_label="Artifact",
        cardinality=Cardinality.ONE_TO_MANY,
        description="Files/chunks inside a submission.",
        property_model="ArtifactCitationProps",
    ),
    # --- assessment ---
    EdgeSpec(
        type=EdgeType.HAS_RUBRIC,
        source_label="Task",
        target_label="Rubric",
        cardinality=Cardinality.MANY_TO_ONE,
        description="Task is graded by this rubric.",
    ),
    EdgeSpec(
        type=EdgeType.HAS_CRITERION,
        source_label="Rubric",
        target_label="RubricCriterion",
        cardinality=Cardinality.ONE_TO_MANY,
        description="Rubric's scope/point criteria.",
    ),
    EdgeSpec(
        type=EdgeType.EVALUATED_BY,
        source_label="Attempt",
        target_label="Assessment",
        cardinality=Cardinality.ONE_TO_MANY,
        description="Assessment run over an attempt.",
        property_model="EvaluationProps",
    ),
    EdgeSpec(
        type=EdgeType.USED_RUBRIC,
        source_label="Assessment",
        target_label="Rubric",
        cardinality=Cardinality.MANY_TO_ONE,
        description="Rubric the assessment applied.",
        property_model="RubricUseProps",
    ),
    EdgeSpec(
        type=EdgeType.SCORED_CRITERION,
        source_label="Assessment",
        target_label="RubricCriterion",
        cardinality=Cardinality.MANY_TO_MANY,
        description="Per-point grader result with confidence and artifact citations.",
        property_model="ScoredCriterionProps",
    ),
    EdgeSpec(
        type=EdgeType.TARGETS_SKILL,
        source_label="RubricCriterion",
        target_label="Skill",
        cardinality=Cardinality.MANY_TO_MANY,
        description="The criterion measures this skill - the hinge from work to skill.",
    ),
    EdgeSpec(
        type=EdgeType.REQUIRES_SKILL,
        source_label="Task",
        target_label="Skill",
        cardinality=Cardinality.MANY_TO_MANY,
        description="Skill the task exercises.",
    ),
    # --- meetings and interactions ---
    EdgeSpec(
        type=EdgeType.PARTICIPATED_IN,
        source_label="Learner",
        target_label="Meeting",
        cardinality=Cardinality.MANY_TO_MANY,
        description="Learner attended a meeting.",
        property_model="ParticipationProps",
    ),
    EdgeSpec(
        type=EdgeType.PARTICIPATED_IN,
        source_label="Learner",
        target_label="Interaction",
        cardinality=Cardinality.MANY_TO_MANY,
        description="Learner took part in an exchange.",
        property_model="ParticipationProps",
    ),
    EdgeSpec(
        type=EdgeType.HELD_FOR_GROUP,
        source_label="Meeting",
        target_label="Group",
        cardinality=Cardinality.MANY_TO_ONE,
        description="Meeting belongs to a group.",
        property_model="MeetingScopeProps",
    ),
    EdgeSpec(
        type=EdgeType.OCCURRED_IN,
        source_label="Interaction",
        target_label="LearningExperience",
        cardinality=Cardinality.MANY_TO_ONE,
        description="Interaction happened inside a task instance.",
        property_model="OccurredInProps",
    ),
    # --- the evidence spine ---
    EdgeSpec(
        type=EdgeType.EVIDENCE_FOR_LEARNER,
        source_label="Evidence",
        target_label="Learner",
        cardinality=Cardinality.MANY_TO_ONE,
        description="Every evidence item is about exactly one learner.",
    ),
    EdgeSpec(
        type=EdgeType.DERIVED_FROM,
        source_label="Evidence",
        target_label="Assessment",
        cardinality=Cardinality.MANY_TO_ONE,
        description="Evidence traced to an assessment.",
        property_model="DerivedFromProps",
    ),
    EdgeSpec(
        type=EdgeType.DERIVED_FROM,
        source_label="Evidence",
        target_label="Submission",
        cardinality=Cardinality.MANY_TO_ONE,
        description="Evidence traced to a submission.",
        property_model="DerivedFromProps",
    ),
    # MANY_TO_MANY: one graded rubric point routinely cites several artifact
    # chunks (``chunks_ids_met`` in the real grader payload).
    EdgeSpec(
        type=EdgeType.DERIVED_FROM,
        source_label="Evidence",
        target_label="Artifact",
        cardinality=Cardinality.MANY_TO_MANY,
        description="Evidence traced to a file/chunk.",
        property_model="DerivedFromProps",
    ),
    EdgeSpec(
        type=EdgeType.DERIVED_FROM,
        source_label="Evidence",
        target_label="Interaction",
        cardinality=Cardinality.MANY_TO_ONE,
        description="Evidence traced to a chat exchange.",
        property_model="DerivedFromProps",
    ),
    EdgeSpec(
        type=EdgeType.DERIVED_FROM,
        source_label="Evidence",
        target_label="Meeting",
        cardinality=Cardinality.MANY_TO_ONE,
        description="Evidence traced to a meeting.",
        property_model="DerivedFromProps",
    ),
    EdgeSpec(
        type=EdgeType.DERIVED_FROM,
        source_label="Evidence",
        target_label="RubricCriterion",
        cardinality=Cardinality.MANY_TO_ONE,
        description="Evidence traced to a rubric point.",
        property_model="DerivedFromProps",
    ),
    EdgeSpec(
        type=EdgeType.DERIVED_FROM,
        source_label="Evidence",
        target_label="LearningExperience",
        cardinality=Cardinality.MANY_TO_ONE,
        description="Evidence traced to a task instance.",
        property_model="DerivedFromProps",
    ),
    EdgeSpec(
        type=EdgeType.EVIDENCE_ABOUT_SKILL,
        source_label="Evidence",
        target_label="Skill",
        cardinality=Cardinality.MANY_TO_MANY,
        description="Which skill this evidence speaks to.",
    ),
    EdgeSpec(
        type=EdgeType.SUPPORTED_BY_EVIDENCE,
        source_label="SkillAssertion",
        target_label="Evidence",
        cardinality=Cardinality.MANY_TO_MANY,
        description="The evidence backing a derived skill claim.",
    ),
    EdgeSpec(
        type=EdgeType.SUPPORTED_BY_EVIDENCE,
        source_label="Observation",
        target_label="Evidence",
        cardinality=Cardinality.MANY_TO_MANY,
        description="The evidence backing a behavioural observation.",
    ),
    # --- derived skill state ---
    EdgeSpec(
        type=EdgeType.HAS_SKILL_ASSERTION,
        source_label="Learner",
        target_label="SkillAssertion",
        cardinality=Cardinality.ONE_TO_MANY,
        description="Learner's derived skill states.",
    ),
    EdgeSpec(
        type=EdgeType.ABOUT_SKILL,
        source_label="SkillAssertion",
        target_label="Skill",
        cardinality=Cardinality.MANY_TO_ONE,
        description="Which skill the assertion concerns.",
    ),
    EdgeSpec(
        type=EdgeType.DECLARED_SKILL,
        source_label="Learner",
        target_label="Skill",
        cardinality=Cardinality.MANY_TO_MANY,
        description="Tier 1: self-declared.",
        property_model="SkillTierProps",
    ),
    EdgeSpec(
        type=EdgeType.EXPOSED_TO_SKILL,
        source_label="Learner",
        target_label="Skill",
        cardinality=Cardinality.MANY_TO_MANY,
        description="Tier 2: learning exposure.",
        property_model="SkillTierProps",
    ),
    EdgeSpec(
        type=EdgeType.ASSESSED_ON_SKILL,
        source_label="Learner",
        target_label="Skill",
        cardinality=Cardinality.MANY_TO_MANY,
        description="Tier 3: scored against a rubric.",
        property_model="SkillTierProps",
    ),
    EdgeSpec(
        type=EdgeType.DEMONSTRATED_SKILL,
        source_label="Learner",
        target_label="Skill",
        cardinality=Cardinality.MANY_TO_MANY,
        description="Tier 4: shipped working artifacts.",
        property_model="SkillTierProps",
    ),
    # --- behaviour ---
    EdgeSpec(
        type=EdgeType.HAS_OBSERVATION,
        source_label="Learner",
        target_label="Observation",
        cardinality=Cardinality.ONE_TO_MANY,
        description="Behavioural observations.",
    ),
    EdgeSpec(
        type=EdgeType.OBSERVED_IN,
        source_label="Observation",
        target_label="Meeting",
        cardinality=Cardinality.MANY_TO_ONE,
        description="Context: a meeting.",
        property_model="ObservedInProps",
    ),
    EdgeSpec(
        type=EdgeType.OBSERVED_IN,
        source_label="Observation",
        target_label="Interaction",
        cardinality=Cardinality.MANY_TO_ONE,
        description="Context: an interaction.",
        property_model="ObservedInProps",
    ),
    EdgeSpec(
        type=EdgeType.OBSERVED_IN,
        source_label="Observation",
        target_label="LearningExperience",
        cardinality=Cardinality.MANY_TO_ONE,
        description="Context: a task instance.",
        property_model="ObservedInProps",
    ),
    # --- career goal and closed loop ---
    EdgeSpec(
        type=EdgeType.HAS_CAREER_GOAL,
        source_label="Learner",
        target_label="CareerGoal",
        cardinality=Cardinality.ONE_TO_ONE,
        description="Current career goal or unknown state.",
    ),
    EdgeSpec(
        type=EdgeType.GOAL_TARGETS_SKILL,
        source_label="CareerGoal",
        target_label="Skill",
        cardinality=Cardinality.MANY_TO_MANY,
        description="Target competency for the goal.",
    ),
    EdgeSpec(
        type=EdgeType.RECOMMENDED_FOR,
        source_label="Recommendation",
        target_label="Learner",
        cardinality=Cardinality.MANY_TO_ONE,
        description="Who the recommendation is for.",
    ),
    EdgeSpec(
        type=EdgeType.RECOMMENDS_SCENARIO,
        source_label="Recommendation",
        target_label="Scenario",
        cardinality=Cardinality.MANY_TO_ONE,
        description="Catalog scenario proposed.",
    ),
    EdgeSpec(
        type=EdgeType.ADDRESSES_GAP_IN,
        source_label="Recommendation",
        target_label="Skill",
        cardinality=Cardinality.MANY_TO_MANY,
        description="Skill the gap concerns.",
    ),
    EdgeSpec(
        type=EdgeType.VALIDATES_SKILL,
        source_label="Scenario",
        target_label="Skill",
        cardinality=Cardinality.MANY_TO_MANY,
        description="What the scenario can prove.",
    ),
    # --- employer access ---
    EdgeSpec(
        type=EdgeType.HAS_ACCESS_GRANT,
        source_label="Employer",
        target_label="AccessGrant",
        cardinality=Cardinality.ONE_TO_MANY,
        description="Grants held by an employer.",
    ),
    EdgeSpec(
        type=EdgeType.GRANTS_ACCESS_TO,
        source_label="AccessGrant",
        target_label="Round",
        cardinality=Cardinality.MANY_TO_MANY,
        description="Rounds the grant unlocks.",
    ),
)

_EDGE_INDEX: dict[tuple[EdgeType, str, str], EdgeSpec] = {
    (s.type, s.source_label, s.target_label): s for s in EDGE_SPECS
}

_PROPERTY_MODELS: dict[str, type[GraphModel]] = {
    "MembershipProps": MembershipProps,
    "CompletedTaskProps": CompletedTaskProps,
    "ParticipationProps": ParticipationProps,
    "SkillTierProps": SkillTierProps,
    "ScoredCriterionProps": ScoredCriterionProps,
    "SubmissionProps": SubmissionProps,
    "SubmittedInProps": SubmittedInProps,
    "ArtifactCitationProps": ArtifactCitationProps,
    "EvaluationProps": EvaluationProps,
    "RubricUseProps": RubricUseProps,
    "MeetingScopeProps": MeetingScopeProps,
    "OccurredInProps": OccurredInProps,
    "DerivedFromProps": DerivedFromProps,
    "ObservedInProps": ObservedInProps,
    "ProjectMembershipProps": ProjectMembershipProps,
}


class Edge(GraphModel):
    """A typed, directed relationship validated against ``EDGE_SPECS``."""

    type: EdgeType
    source_label: str
    source_id: UUID
    target_label: str
    target_id: UUID
    properties: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_against_registry(self) -> "Edge":
        key = (self.type, self.source_label, self.target_label)
        spec = _EDGE_INDEX.get(key)
        if spec is None:
            legal = sorted(
                f"({s.source_label})-[:{s.type.value}]->({s.target_label})"
                for s in EDGE_SPECS
                if s.type is self.type
            )
            raise ValueError(
                f"illegal relationship "
                f"({self.source_label})-[:{self.type.value}]->({self.target_label}). "
                + (
                    f"Legal forms for {self.type.value}: {legal}"
                    if legal
                    else f"{self.type.value} has no registered endpoints."
                )
            )
        if spec.property_model:
            model = _PROPERTY_MODELS[spec.property_model]
            # Validate, then round-trip so the stored dict is normalised.
            object.__setattr__(
                self,
                "properties",
                model.model_validate(self.properties).model_dump(mode="json"),
            )
        elif self.properties:
            raise ValueError(
                f"{self.type.value} takes no properties but got "
                f"{sorted(self.properties)}"
            )
        return self

    @property
    def spec(self) -> EdgeSpec:
        return _EDGE_INDEX[(self.type, self.source_label, self.target_label)]

    def __str__(self) -> str:  # pragma: no cover - debugging aid
        return f"({self.source_label})-[:{self.type.value}]->({self.target_label})"


# ===========================================================================
# The graph container - where the structural invariants are enforced
# ===========================================================================


class LearnerGraph(GraphModel):
    """A validated slice of the Professional Learner Graph.

    Validation performed here, in order:
      1. every node id is unique;
      2. every edge endpoint exists and its declared label matches the node;
      3. every edge is a legal (type, source, target) triple  [in ``Edge``];
      4. declared cardinality is respected;
      5. Evidence-First: every derived claim has evidence, and every
         evidence item is traceable to a source record and a learner.
    """

    schema_version: str = SCHEMA_VERSION
    ontology_version: str = ONTOLOGY_VERSION
    generated_at: UtcDatetime
    description: str | None = None
    nodes: list[AnyNode]
    edges: list[Edge] = Field(default_factory=list)

    # -- lookups ------------------------------------------------------------

    def index(self) -> dict[UUID, GraphNode]:
        return {n.id: n for n in self.nodes}

    def by_label(self, label: str) -> list[GraphNode]:
        return [n for n in self.nodes if n.label == label]

    def edges_of(
        self,
        edge_type: EdgeType,
        source_id: UUID | None = None,
        target_id: UUID | None = None,
    ) -> list[Edge]:
        return [
            e
            for e in self.edges
            if e.type is edge_type
            and (source_id is None or e.source_id == source_id)
            and (target_id is None or e.target_id == target_id)
        ]

    # -- validators ---------------------------------------------------------

    @model_validator(mode="after")
    def _unique_node_ids(self) -> "LearnerGraph":
        seen: dict[UUID, str] = {}
        dupes: list[str] = []
        for n in self.nodes:
            if n.id in seen:
                dupes.append(f"{n.id} used by {seen[n.id]} and {n.label}")
            seen[n.id] = n.label
        if dupes:
            raise ValueError("duplicate node ids: " + "; ".join(dupes))
        return self

    @model_validator(mode="after")
    def _edges_resolve(self) -> "LearnerGraph":
        idx = self.index()
        problems: list[str] = []
        for e in self.edges:
            for role, nid, lbl in (
                ("source", e.source_id, e.source_label),
                ("target", e.target_id, e.target_label),
            ):
                node = idx.get(nid)
                if node is None:
                    problems.append(f"{e}: {role} {nid} does not exist")
                elif node.label != lbl:  # type: ignore[attr-defined]
                    problems.append(
                        f"{e}: {role} {nid} is a {node.label} but the edge says {lbl}"  # type: ignore[attr-defined]
                    )
        if problems:
            raise ValueError("dangling or mislabelled edges: " + "; ".join(problems))
        return self

    @model_validator(mode="after")
    def _cardinality(self) -> "LearnerGraph":
        from collections import Counter

        problems: list[str] = []
        for spec in EDGE_SPECS:
            rel = [
                e
                for e in self.edges
                if e.type is spec.type
                and e.source_label == spec.source_label
                and e.target_label == spec.target_label
            ]
            if not rel:
                continue
            out = Counter(e.source_id for e in rel)
            inn = Counter(e.target_id for e in rel)
            sig = f"({spec.source_label})-[:{spec.type.value}]->({spec.target_label})"
            if spec.cardinality in (Cardinality.ONE_TO_ONE, Cardinality.MANY_TO_ONE):
                bad = [f"{k} has {v}" for k, v in out.items() if v > 1]
                if bad:
                    problems.append(
                        f"{sig} is {spec.cardinality.value}; source(s) with >1 edge: "
                        f"{bad}"
                    )
            if spec.cardinality in (Cardinality.ONE_TO_ONE, Cardinality.ONE_TO_MANY):
                bad = [f"{k} has {v}" for k, v in inn.items() if v > 1]
                if bad:
                    problems.append(
                        f"{sig} is {spec.cardinality.value}; target(s) with >1 edge: "
                        f"{bad}"
                    )
        if problems:
            raise ValueError("cardinality violations: " + "; ".join(problems))
        return self

    @model_validator(mode="after")
    def _provenance_tuple_consistent(self) -> "LearnerGraph":
        """Every DERIVED_FROM edge must repeat its Evidence node's tuple exactly.

        The tuple is duplicated onto the edge so Neo4j can filter traceability
        links without touching the node. Duplication invites drift, so this
        check makes drift a construction error rather than a silent data bug.
        """
        idx = self.index()
        problems: list[str] = []
        for e in self.edges:
            if e.type is not EdgeType.DERIVED_FROM or not e.properties:
                continue
            node = idx.get(e.source_id)
            if not isinstance(node, Evidence):
                continue
            prov = node.provenance
            expected = {
                "source_system": prov.source_system.value,
                "source_id": prov.source_id,
                "evidence_type": node.evidence_type.value,
            }
            for key, want in expected.items():
                got = e.properties.get(key)
                if got != want:
                    problems.append(
                        f"DERIVED_FROM edge from Evidence {node.id}: "
                        f"{key}={got!r} on the edge but {want!r} on the node"
                    )
        if problems:
            raise ValueError(
                "provenance tuple drift between edge and node: " + "; ".join(problems)
            )
        return self

    @model_validator(mode="after")
    def _evidence_first(self) -> "LearnerGraph":
        """The structural guarantee behind the Evidence-First Principle.

        A derived claim with no evidence, or an evidence item with no
        traceable origin, is a schema error - not a warning.
        """
        problems: list[str] = []

        supported = {
            e.source_id for e in self.edges if e.type is EdgeType.SUPPORTED_BY_EVIDENCE
        }

        for a in self.by_label("SkillAssertion"):
            assert isinstance(a, SkillAssertion)
            has_ev = a.id in supported
            if a.status is AssertionStatus.NO_EVIDENCE:
                if has_ev:
                    problems.append(
                        f"SkillAssertion {a.id} is status=no_evidence but has "
                        f"SUPPORTED_BY_EVIDENCE edges"
                    )
            elif not has_ev:
                problems.append(
                    f"SkillAssertion {a.id} (status={a.status.value}) has no "
                    f"SUPPORTED_BY_EVIDENCE edge - unsupported claims are not storable"
                )
            if not self.edges_of(EdgeType.ABOUT_SKILL, source_id=a.id):
                problems.append(
                    f"SkillAssertion {a.id} is not linked to a Skill via ABOUT_SKILL"
                )

        for o in self.by_label("Observation"):
            if o.id not in supported:
                problems.append(f"Observation {o.id} has no SUPPORTED_BY_EVIDENCE edge")

        for ev in self.by_label("Evidence"):
            if not self.edges_of(EdgeType.DERIVED_FROM, source_id=ev.id):
                problems.append(f"Evidence {ev.id} has no DERIVED_FROM source record")
            if not self.edges_of(EdgeType.EVIDENCE_FOR_LEARNER, source_id=ev.id):
                problems.append(f"Evidence {ev.id} is not attached to a Learner")

        if problems:
            raise ValueError("Evidence-First violations: " + "; ".join(problems))
        return self

    # -- reporting ----------------------------------------------------------

    def counts(self) -> dict[str, int]:
        from collections import Counter

        return dict(sorted(Counter(n.label for n in self.nodes).items()))

    def edge_counts(self) -> dict[str, int]:
        from collections import Counter

        return dict(
            sorted(Counter(str(e) + f" [{e.type.value}]" for e in self.edges).items())
        )

    def evidence_for_skill(self, learner_id: UUID, skill_id: UUID) -> list[Evidence]:
        """All evidence backing any assertion this learner holds for a skill.

        This is the Python mirror of the Cypher traversal that Epic 2 runs to
        answer "Does she know X? Show me the evidence."
        """
        idx = self.index()
        assertion_ids = {
            e.source_id for e in self.edges_of(EdgeType.ABOUT_SKILL, target_id=skill_id)
        } & {
            e.target_id
            for e in self.edges_of(EdgeType.HAS_SKILL_ASSERTION, source_id=learner_id)
        }
        out: list[Evidence] = []
        for aid in assertion_ids:
            for e in self.edges_of(EdgeType.SUPPORTED_BY_EVIDENCE, source_id=aid):
                node = idx.get(e.target_id)
                if isinstance(node, Evidence) and node not in out:
                    out.append(node)
        return sorted(out, key=lambda x: x.observed_at, reverse=True)
