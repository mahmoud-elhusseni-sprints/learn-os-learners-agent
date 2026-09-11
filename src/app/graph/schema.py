"""
Professional Learner Graph - ontology (v2, minimal).

REWRITTEN from a 26-node design to 3 nodes, per the mentor's rejection of
the previous schema and the architecture literally specified in the
mentor-authored MD file ("3 Nodes Only": LearnerProfile, DataSource,
MemoryCard).

What changed and why
---------------------
The previous version normalised every source record into its own node type
(Task, Submission, Assessment, RubricCriterion, Evidence, SkillAssertion,
Meeting, ...) and connected them with 53 typed relationships. The mentor's
feedback was that this is too many nodes. The MD file's own answer is to
collapse almost everything into one node - ``DataSource`` - whose
``payload`` field holds the whole review/assessment record as one embedded
object, discriminated by ``datasource_name``.

This is a genuine architectural reversal, not a trim:

  * Evidence, Assessment, Submission, RubricCriterion, Task,
    LearningExperience, Attempt, Artifact, Meeting, Interaction, Skill,
    SkillAssertion, Observation, CareerGoal, Scenario, Recommendation,
    Employer, AccessGrant, Cohort, Round, Group, LearnerIdentity, Rubric,
    Project, AssessmentAnswer - all REMOVED as separate nodes. Their data
    now lives inside ``DataSource.payload`` (for review/assessment content)
    or is simply not modelled (Cohort/Round/Group/Employer/AccessGrant have
    no equivalent in the MD file at all - see the handoff report for what
    this costs).

  * The "Evidence-First" structural invariant - the validator that made it
    impossible to construct a skill claim with no supporting evidence node -
    is RETIRED. It protected a graph of separate Evidence/SkillAssertion
    nodes that no longer exist. There is nothing analogous to enforce here;
    a DataSource's payload is trusted as delivered. This is a real loss of
    guarantee, flagged in the handoff report, not smoothed over.

  * Provenance as a first-class field group (source_system / source_id /
    evidence_type on every node) is also gone. ``DataSource`` carries
    ``datasource_id`` and ``datasource_name`` and a ``timestamp``, which is
    the MD file's own version of provenance, but ``LearnerProfile`` and
    ``MemoryCard`` carry none. This is the MD file's design, not an
    oversight in this rewrite - also flagged in the handoff report.

What is kept from the previous version, because nothing in the MD file
argues against it:

  * ``extra="forbid"`` on every model - a typo in a field name still fails
    loudly instead of silently creating an orphan property.
  * UTC-enforced timestamps.
  * Deterministic (UUIDv5) node identifiers, so re-ingestion cannot
    duplicate a node - this is a general database-integrity property, not
    part of the ontology the MD file is describing, and the MD file does
    not remove the requirement (Sprint 1 acceptance still requires it).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

ONTOLOGY_VERSION = "0.2.0"
SCHEMA_VERSION = "learner-graph/0.2.0"


# ===========================================================================
# Timestamp handling - unchanged from v1: reject naive datetimes, normalise
# to UTC. Nothing in the MD file argues this should change.
# ===========================================================================


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError(
            "timestamp must be timezone-aware ISO 8601 "
            "(e.g. '2026-07-30T10:17:08.550Z' or '...+00:00'); got a naive datetime"
        )
    return value.astimezone(timezone.utc)


UtcDatetime = Annotated[datetime, AfterValidator(_require_utc)]
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]


# ===========================================================================
# Controlled vocabularies - values taken verbatim from the MD file,
# including its literal spelling, since ingestion will produce that exact
# string.
# ===========================================================================


class LearnerRole(str, Enum):
    """MD §1: "role can be 'lead' or 'member'"."""

    LEAD = "lead"
    MEMBER = "member"


class DataSourceName(str, Enum):
    """MD §2: the four named datasource_name values, verbatim.

    'assesments' is misspelled in the MD file and in the upstream data this
    models. Kept as-is rather than corrected, because correcting it would
    make this enum stop matching the strings the ingestion pipeline
    actually produces.
    """

    REVIEW = "review"
    ASSESSMENTS = "assesments"  # sic - matches the MD file / source data
    CHAT = "chat"  # stub - owned by a different task
    MEETINGS = "meetings"  # stub - owned by a different task


class RubricPointStatus(str, Enum):
    """Status values used inside a review payload's rubric evaluations."""

    YES = "Yes"
    PARTIAL = "Partial"
    NO = "No"


# ===========================================================================
# Base model - unchanged behaviour from v1.
# ===========================================================================


class GraphModel(BaseModel):
    """``extra='forbid'``: a typo in a field name fails immediately instead
    of silently creating an orphan property."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )


class GraphNode(GraphModel):
    """Every node has a deterministic id and a creation timestamp."""

    id: str = Field(description="Deterministic id - see src/app/graph/ids.py")
    created_at: UtcDatetime
    label: str


# ===========================================================================
# Embedded payload variants (MD §2)
#
# The MD file embeds these as a raw dict inside DataSource.payload. Modelled
# here as typed sub-objects, still embedded on the same DataSource node
# (never their own node), so that "Data Validation Models... enforcing
# property validation" from the original task brief is still satisfied
# without reintroducing separate nodes. If a completely untyped dict is
# preferred instead, say so - this is the one place this rewrite added
# structure beyond what the MD file's own field list strictly required.
# ===========================================================================


class RubricPointEvaluation(GraphModel):
    """One entry in ``review`` payload's ``detailed_rubric_evaluations``."""

    rubric_id: int
    category: str
    requirement: str
    status: RubricPointStatus
    evaluation_criteria: str
    reason: str
    confidence_score: Confidence


class ReviewPayload(GraphModel):
    """``datasource_name == "review"`` - Task Submission + Mentor Rubric
    Evaluation, combined into one embedded object per the MD file."""

    lx_id: str = Field(description="Task / Learning Experience id")
    task_headline: str
    attempt_number: int = Field(ge=1)
    hours_before_deadline: float | None = Field(
        default=None,
        description="Hours between submission and the task deadline. "
        "Negative means submitted late. None means the deadline could not "
        "be determined from the source record - deliberately distinct "
        "from 0.0 (submitted exactly at the deadline), which is a real "
        "value, not a stand-in for 'unknown'.",
    )
    submission_text: str
    assets: list[str] = Field(
        default_factory=list,
        description="Combined code_repositories + media_assets per the MD file.",
    )
    verdict: str
    feedback_summary: str
    mentor_reply: str
    detailed_rubric_evaluations: list[RubricPointEvaluation] = Field(
        default_factory=list
    )


class AssessmentAnswerItem(GraphModel):
    """One entry in ``assesments`` payload's ``answers``."""

    question_id: str
    domain: str
    metric_key: str
    learner_answer: str
    score: float = Field(ge=0)
    evaluation_notes: str


class AssessmentPayload(GraphModel):
    """``datasource_name == "assesments"`` - an LMS-style assessment."""

    lx_id: str
    assessment_type: str
    topic_id: str
    score: float = Field(ge=0)
    max_score: float = Field(ge=0)
    answers: list[AssessmentAnswerItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def _score_within_max(self) -> "AssessmentPayload":
        if self.score > self.max_score:
            raise ValueError(f"score {self.score} exceeds max_score {self.max_score}")
        return self


class StubPayload(GraphModel):
    """``datasource_name in ("chat", "meetings")`` - owned by another task.

    The MD file marks both as ``payload={}``. Modelled as an explicit empty
    shape rather than an untyped dict, so a chat/meetings DataSource cannot
    silently accumulate fields that belong to the review/assessment shapes.
    """

    model_config = ConfigDict(extra="forbid")


# ===========================================================================
# The three nodes
# ===========================================================================


class LearnerProfile(GraphNode):
    """MD §1. The canonical person and their programme placement."""

    label: Literal["LearnerProfile"] = "LearnerProfile"
    learner_id: str = Field(description="Source system's learner id")
    name: str
    role: LearnerRole
    group_name: str
    round_name: str
    added_at: UtcDatetime
    learner_status: str | None = Field(
        default=None,
        description=(
            "Whether the learner is active. The MD file notes this 'can be "
            "removed' - kept as optional per that note rather than deleted, "
            "since the field is still listed. Confirm with the mentor "
            "whether to drop it entirely."
        ),
    )


class DataSource(GraphNode):
    """MD §2. One record from one of four source systems, keyed by
    ``datasource_name``. The embedded ``payload`` is where almost all of
    the previous schema's separate node types now live.
    """

    label: Literal["DataSource"] = "DataSource"
    datasource_id: str
    datasource_name: DataSourceName
    timestamp: UtcDatetime
    payload: ReviewPayload | AssessmentPayload | StubPayload

    @model_validator(mode="after")
    def _payload_matches_datasource_name(self) -> "DataSource":
        expected = {
            DataSourceName.REVIEW: ReviewPayload,
            DataSourceName.ASSESSMENTS: AssessmentPayload,
            DataSourceName.CHAT: StubPayload,
            DataSourceName.MEETINGS: StubPayload,
        }[self.datasource_name]
        if not isinstance(self.payload, expected):
            raise ValueError(
                f"datasource_name={self.datasource_name.value!r} requires a "
                f"{expected.__name__} payload, got {type(self.payload).__name__}"
            )
        return self


class MemoryCard(GraphNode):
    """MD §3. A short, tagged insight extracted from a source record."""

    label: Literal["MemoryCard"] = "MemoryCard"
    card_id: str
    metric_key: str
    content: str
    rationale: str | None = None
    tags: list[str] = Field(
        default_factory=list,
        description="Canonical competency tags associated with this memory card.",
    )
    created_at: UtcDatetime


AnyNode = Annotated[
    Union[LearnerProfile, DataSource, MemoryCard],
    Field(discriminator="label"),
]

NODE_CLASSES: dict[str, type[GraphNode]] = {
    cls.model_fields["label"].default: cls
    for cls in (LearnerProfile, DataSource, MemoryCard)
}


# ===========================================================================
# Relationships (MD "Relationships & Architecture Notes")
#
# Exactly the three edges the MD file draws. No others are invented.
# ===========================================================================


class EdgeType(str, Enum):
    PRODUCED = "PRODUCED"
    EXTRACTED_INTO = "EXTRACTED_INTO"
    HAS_MEMORY_CARD = "HAS_MEMORY_CARD"
    # The MD file offers "HAS_MEMORY_CARD / ASSOCIATED_WITH" as two names for
    # the same relationship. HAS_MEMORY_CARD was chosen as the canonical
    # name; ASSOCIATED_WITH is not a second, different edge type.


class Cardinality(str, Enum):
    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_ONE = "N:1"
    MANY_TO_MANY = "N:M"


class EdgeSpec(GraphModel):
    type: EdgeType
    source_label: str
    target_label: str
    cardinality: Cardinality
    description: str


EDGE_SPECS: tuple[EdgeSpec, ...] = (
    EdgeSpec(
        type=EdgeType.PRODUCED,
        source_label="LearnerProfile",
        target_label="DataSource",
        cardinality=Cardinality.ONE_TO_MANY,
        description="A learner produces many source records over time.",
    ),
    EdgeSpec(
        type=EdgeType.EXTRACTED_INTO,
        source_label="DataSource",
        target_label="MemoryCard",
        cardinality=Cardinality.ONE_TO_MANY,
        description=(
            "One source record (e.g. a review with several rubric points, "
            "or an assessment with several answers) can be distilled into "
            "several memory cards."
        ),
    ),
    EdgeSpec(
        type=EdgeType.HAS_MEMORY_CARD,
        source_label="LearnerProfile",
        target_label="MemoryCard",
        cardinality=Cardinality.MANY_TO_MANY,
        description=(
            "Direct link from learner to memory card, drawn explicitly in "
            "the MD file's architecture notes as many-to-many, in addition "
            "to the indirect path via DataSource."
        ),
    ),
)

_EDGE_INDEX: dict[tuple[EdgeType, str, str], EdgeSpec] = {
    (s.type, s.source_label, s.target_label): s for s in EDGE_SPECS
}


class Edge(GraphModel):
    """A typed, directed relationship validated against ``EDGE_SPECS``."""

    type: EdgeType
    source_label: str
    source_id: str
    target_label: str
    target_id: str

    @model_validator(mode="after")
    def _validate_against_registry(self) -> "Edge":
        key = (self.type, self.source_label, self.target_label)
        if key not in _EDGE_INDEX:
            legal = sorted(
                f"({s.source_label})-[:{s.type.value}]->({s.target_label})"
                for s in EDGE_SPECS
                if s.type is self.type
            )
            raise ValueError(
                f"illegal relationship "
                f"({self.source_label})-[:{self.type.value}]->({self.target_label}). "
                f"Legal forms for {self.type.value}: {legal}"
            )
        return self

    def __str__(self) -> str:  # pragma: no cover - debugging aid
        return f"({self.source_label})-[:{self.type.value}]->({self.target_label})"


# ===========================================================================
# The graph container
#
# Structural checks kept: unique ids, edges resolve, edges match the
# registry, cardinality holds. The "Evidence-First" invariant from v1 is
# NOT reintroduced here - see the module docstring for why.
# ===========================================================================


class LearnerGraph(GraphModel):
    schema_version: str = SCHEMA_VERSION
    ontology_version: str = ONTOLOGY_VERSION
    generated_at: UtcDatetime
    description: str | None = None
    nodes: list[AnyNode]
    edges: list[Edge] = Field(default_factory=list)

    def index(self) -> dict[str, GraphNode]:
        return {n.id: n for n in self.nodes}

    def by_label(self, label: str) -> list[GraphNode]:
        return [n for n in self.nodes if n.label == label]

    def edges_of(
        self,
        edge_type: EdgeType,
        source_id: str | None = None,
        target_id: str | None = None,
    ) -> list[Edge]:
        return [
            e
            for e in self.edges
            if e.type is edge_type
            and (source_id is None or e.source_id == source_id)
            and (target_id is None or e.target_id == target_id)
        ]

    @model_validator(mode="after")
    def _unique_node_ids(self) -> "LearnerGraph":
        seen: dict[str, str] = {}
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
                elif node.label != lbl:
                    problems.append(
                        f"{e}: {role} {nid} is a {node.label} but the edge says {lbl}"
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
                        f"{sig} is {spec.cardinality.value}; "
                        f"source(s) with >1 edge: {bad}"
                    )
            if spec.cardinality in (Cardinality.ONE_TO_ONE, Cardinality.ONE_TO_MANY):
                bad = [f"{k} has {v}" for k, v in inn.items() if v > 1]
                if bad:
                    problems.append(
                        f"{sig} is {spec.cardinality.value}; "
                        f"target(s) with >1 edge: {bad}"
                    )
        if problems:
            raise ValueError("cardinality violations: " + "; ".join(problems))
        return self

    def counts(self) -> dict[str, int]:
        from collections import Counter

        return dict(sorted(Counter(n.label for n in self.nodes).items()))
