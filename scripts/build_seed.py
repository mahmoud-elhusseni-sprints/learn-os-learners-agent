"""
Build ``sample_learner_seed.json`` from the real anonymized internship export.

Why build the fixture from real data instead of inventing one
-------------------------------------------------------------
A hand-written fixture only proves the models are self-consistent.  Building
it from the actual export proves the ontology *fits the data the ingestion
pipeline (Task 3) will receive* - which is the only thing that matters for
Sprint 1 integration.

The seed reconstructs one learner (Learner A4, the richest profile in the
Group A export: 7 task instances, 5 graded submissions across multiple
attempts, 18 meeting memory cards) and links their skills to evidence drawn
from FOUR distinct source systems:

    virtual_internship  - task instances, submissions, chat interactions
    assessment_engine   - per-rubric-point grader results with confidence
    meeting_memory      - structured facts extracted from Zoom transcripts
    meetings            - the meetings those facts came from

Usage
-----
    python3 build_seed.py --logs-dir "/path/to/AI Internship Logs/group-a-ai-engineer"

The generated fixture is committed; this script exists so it can be
regenerated and audited rather than trusted blindly.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import UUID

import src.app.graph.schema as M
from src.app.graph.ids import (
    assertion_uid,
    deterministic_id,
    evidence_uid,
    learner_uid,
    observation_uid,
    skill_uid,
)

# The export is anonymized, but a couple of repository URLs still carry a real
# GitHub handle (the export README flags this as a known limitation for strings
# glued to other text).  Scrub it so the committed fixture is clean.
_REDACTIONS = {"MoHatemTC": "learner-a4"}

TARGET_LEARNER_ID = "900353f6-f011-4d31-9a8a-b050b891c69c"  # Learner A4
INGESTED_AT = datetime(2026, 8, 31, 12, 0, 0, tzinfo=timezone.utc)
BUILDER = "seed-builder@0.1.0"


def redact(text: str | None) -> str | None:
    if text is None:
        return None
    for bad, good in _REDACTIONS.items():
        text = text.replace(bad, good)
    return text


def ts(value: str | None) -> datetime | None:
    if not value:
        return None
    v = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(v)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


# ===========================================================================
# Canonical skill registry
#
# Seeded from what actually appears in this learner's tasks, rubrics and
# meeting cards.  In production this becomes the taxonomy service the PRD
# calls for ("canonical skill registry + aliases + mapping governance");
# here it is a small, explicit table so the mapping is auditable.
# ===========================================================================

SKILL_REGISTRY: list[dict[str, Any]] = [
    {
        "name": "Python",
        "slug": "python",
        "category": M.SkillCategory.DIGITAL_AI_SKILLS,
        "aliases": ["python 3.11", "python3", "py"],
    },
    {
        "name": "FastAPI",
        "slug": "fastapi",
        "category": M.SkillCategory.DIGITAL_AI_SKILLS,
        "aliases": ["fast api"],
    },
    {
        "name": "PostgreSQL",
        "slug": "postgresql",
        "category": M.SkillCategory.DIGITAL_AI_SKILLS,
        "aliases": ["postgres", "psql"],
    },
    {
        "name": "Pydantic",
        "slug": "pydantic",
        "category": M.SkillCategory.DIGITAL_AI_SKILLS,
        "aliases": ["pydantic v2"],
    },
    {
        "name": "Automated Testing",
        "slug": "automated-testing",
        "category": M.SkillCategory.WORK_SKILLS,
        "aliases": ["pytest", "unit test", "test coverage"],
    },
    {
        "name": "React",
        "slug": "react",
        "category": M.SkillCategory.DIGITAL_AI_SKILLS,
        "aliases": ["react.js", "reactjs", "frontend in react"],
    },
    {
        "name": "REST API Design",
        "slug": "rest-api",
        "category": M.SkillCategory.DIGITAL_AI_SKILLS,
        "aliases": ["rest api", "restful api", "restful apis", "rest"],
    },
    {
        "name": "Supabase",
        "slug": "supabase",
        "category": M.SkillCategory.DIGITAL_AI_SKILLS,
        "aliases": [],
    },
    {
        "name": "Prompt Engineering",
        "slug": "prompt-engineering",
        "category": M.SkillCategory.DIGITAL_AI_SKILLS,
        "aliases": ["prompt enhancement", "prompting"],
    },
    {
        "name": "Large Language Models",
        "slug": "llm",
        "category": M.SkillCategory.DIGITAL_AI_SKILLS,
        "aliases": ["llm", "llms", "groq"],
    },
    {
        "name": "Async Programming",
        "slug": "async-programming",
        "category": M.SkillCategory.DIGITAL_AI_SKILLS,
        "aliases": ["async", "async functions", "async job queue", "asynchronous"],
    },
    {
        "name": "Data Schema Design",
        "slug": "data-schema-design",
        "category": M.SkillCategory.DIGITAL_AI_SKILLS,
        "aliases": ["data schema", "db schema", "database schema", "schema migration"],
    },
    {
        "name": "Pipeline Orchestration",
        "slug": "pipeline-orchestration",
        "category": M.SkillCategory.DIGITAL_AI_SKILLS,
        "aliases": ["orchestrator", "pipeline integration", "pipeline"],
    },
    {
        "name": "Git",
        "slug": "git",
        "category": M.SkillCategory.WORK_SKILLS,
        "aliases": ["github", "pull request", "branch"],
    },
    {
        "name": "CI/CD",
        "slug": "ci-cd",
        "category": M.SkillCategory.WORK_SKILLS,
        "aliases": ["circleci", "continuous integration", "workflow actions"],
    },
    {
        "name": "Remotion",
        "slug": "remotion",
        "category": M.SkillCategory.DIGITAL_AI_SKILLS,
        "aliases": [],
    },
    {
        "name": "Vector Databases",
        "slug": "vector-databases",
        "category": M.SkillCategory.DIGITAL_AI_SKILLS,
        "aliases": ["qdrant", "vector db"],
    },
    {
        "name": "Error Handling",
        "slug": "error-handling",
        "category": M.SkillCategory.WORK_SKILLS,
        "aliases": ["input validation", "edge cases", "error logging"],
    },
]

_SKILL_LOOKUP: list[tuple[str, dict[str, Any]]] = []
for _s in SKILL_REGISTRY:
    for _term in [_s["name"].lower(), _s["slug"].replace("-", " "), *_s["aliases"]]:
        _SKILL_LOOKUP.append((_term, _s))
_SKILL_LOOKUP.sort(key=lambda kv: -len(kv[0]))


def match_skills(*texts: str | None, limit: int = 4) -> list[dict[str, Any]]:
    """Find canonical skills mentioned in free text.

    Deliberately conservative word-boundary matching: over-matching here would
    manufacture evidence, which is exactly what the Evidence-First Principle
    exists to prevent.
    """
    blob = " ".join(t.lower() for t in texts if t)
    found: list[dict[str, Any]] = []
    for term, skill in _SKILL_LOOKUP:
        if skill in found:
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", blob):
            found.append(skill)
        if len(found) >= limit:
            break
    return found


# ===========================================================================
# Builder
# ===========================================================================


class SeedBuilder:
    def __init__(self, logs_dir: Path) -> None:
        self.dir = logs_dir
        self.nodes: list[M.GraphNode] = []
        self.edges: list[M.Edge] = []
        self._ids: set[UUID] = set()
        self.skill_nodes: dict[str, M.Skill] = {}
        # skill slug -> tier -> list of Evidence
        self.skill_evidence: dict[str, dict[M.SkillEvidenceTier, list[M.Evidence]]] = {}

    # -- plumbing -----------------------------------------------------------

    def add(self, node: M.GraphNode) -> M.GraphNode:
        if node.id in self._ids:
            return next(n for n in self.nodes if n.id == node.id)
        self._ids.add(node.id)
        self.nodes.append(node)
        return node

    def link(
        self, etype: M.EdgeType, src: M.GraphNode, dst: M.GraphNode, **props: Any
    ) -> None:
        edge = M.Edge(
            type=etype,
            source_label=src.label,
            source_id=src.id,  # type: ignore[attr-defined]
            target_label=dst.label,
            target_id=dst.id,  # type: ignore[attr-defined]
            properties=props,
        )
        if not any(
            e.type is edge.type
            and e.source_id == edge.source_id
            and e.target_id == edge.target_id
            for e in self.edges
        ):
            self.edges.append(edge)

    def prov(
        self,
        system: M.SourceSystem,
        stype: str,
        sid: str,
        observed: datetime,
        locator: str | None = None,
        url: str | None = None,
        method: M.ExtractionMethod = M.ExtractionMethod.DIRECT_MAPPING,
        evidence_type: M.EvidenceType | None = None,
    ) -> M.Provenance:
        """Build a provenance record.

        Passing ``evidence_type`` returns an ``EvidenceProvenance``, the
        stricter type that Evidence nodes require - it makes the full
        (source_system, source_id, timestamp, evidence_type) tuple mandatory.
        """
        fields: dict[str, Any] = dict(
            source_system=system,
            source_type=stype,
            source_id=str(sid),
            source_locator=locator,
            source_url=url,
            observed_at=observed,
            ingested_at=INGESTED_AT,
            extraction_method=method,
        )
        if evidence_type is not None:
            return M.EvidenceProvenance(evidence_type=evidence_type, **fields)
        return M.Provenance(**fields)

    @staticmethod
    def evidence_tuple(ev: M.Evidence) -> dict[str, Any]:
        """The provenance tuple a DERIVED_FROM edge must repeat.

        Read straight off the Evidence node so the edge copy cannot disagree
        with it - LearnerGraph rejects the graph if it ever does.
        """
        return {
            "source_system": ev.provenance.source_system.value,
            "source_id": ev.provenance.source_id,
            "observed_at": ev.observed_at.isoformat(),
            "evidence_type": ev.evidence_type.value,
        }

    def skill(self, spec: dict[str, Any]) -> M.Skill:
        if spec["slug"] not in self.skill_nodes:
            node = M.Skill(
                id=skill_uid(spec["slug"]),
                created_at=INGESTED_AT,
                canonical_name=spec["name"],
                slug=spec["slug"],
                category=spec["category"],
                aliases=spec["aliases"],
            )
            self.skill_nodes[spec["slug"]] = node  # type: ignore[assignment]
            self.add(node)
        return self.skill_nodes[spec["slug"]]

    def record_skill_evidence(
        self, slug: str, tier: M.SkillEvidenceTier, ev: M.Evidence
    ) -> None:
        self.skill_evidence.setdefault(slug, {}).setdefault(tier, []).append(ev)

    # -- build steps --------------------------------------------------------

    def build(self) -> M.LearnerGraph:
        learner = self.build_scope_and_learner()
        lx_rows = self.build_tasks(learner)
        self.build_interactions_and_assessments(learner, lx_rows)
        self.build_delivered_work_from_outcomes(learner, lx_rows)
        self.build_meetings_and_observations(learner)
        self.build_skill_assertions(learner)
        self.build_career_goal(learner)
        self.build_employer_access()
        self.backfill_derived_counts()
        return M.LearnerGraph(
            generated_at=INGESTED_AT,
            description=(
                "Sprint 1 / Task 2 seed fixture. One learner (Learner A4) "
                "reconstructed "
                "from the anonymized Group A internship export, with skill claims "
                "traced "
                "to evidence from four distinct source systems."
            ),
            nodes=self.nodes,
            edges=self.edges,
        )

    def backfill_derived_counts(self) -> None:
        """Fill counters that are only knowable once the graph is complete.

        ``Submission.artifact_count`` depends on how many artifacts the grader
        ended up citing, which is not known while the submission node is being
        created.
        """
        per_submission: dict[Any, int] = {}
        for edge in self.edges:
            if edge.type is M.EdgeType.CONTAINS_ARTIFACT:
                per_submission[edge.source_id] = (
                    per_submission.get(edge.source_id, 0) + 1
                )
        for node in self.nodes:
            if isinstance(node, M.Submission):
                node.artifact_count = per_submission.get(node.id, 0)

    # ---- scope + identity -------------------------------------------------

    def build_scope_and_learner(self) -> M.Learner:
        row = next(
            r
            for r in jsonl(self.dir / "learners.jsonl")
            if r["learner_id"] == TARGET_LEARNER_ID
        )
        added = ts(row["added_at"]) or INGESTED_AT

        cfg = next(iter(jsonl(self.dir / "lx_configs.jsonl")))
        intern = cfg["config_json"]["internship"]["internship"]

        cohort = self.add(
            M.Cohort(
                id=deterministic_id(
                    "virtual_internship", "cohort", intern["cohort_id"]
                ),
                created_at=INGESTED_AT,
                provenance=self.prov(
                    M.SourceSystem.VIRTUAL_INTERNSHIP,
                    "internship",
                    intern["cohort_id"],
                    added,
                ),
                cohort_key=intern["cohort_id"],
                name=intern["name"],
                start_date=ts(intern["start_date"] + "T00:00:00+00:00"),
                end_date=ts(intern["end_date"] + "T00:00:00+00:00"),
                duration_weeks=intern.get("duration_weeks"),
                organization_id=cfg.get("config_json", {})
                .get("actors", {})
                .get("mentor", {})
                .get("persona", {})
                .get("organization_id"),
            )
        )
        rnd = self.add(
            M.Round(
                id=deterministic_id("virtual_internship", "round", row["round_name"]),
                created_at=INGESTED_AT,
                provenance=self.prov(
                    M.SourceSystem.VIRTUAL_INTERNSHIP, "round", row["round_name"], added
                ),
                round_key=row["round_name"],
                name=row["round_name"],
            )
        )
        grp = self.add(
            M.Group(
                id=deterministic_id("virtual_internship", "group", row["group_id"]),
                created_at=INGESTED_AT,
                provenance=self.prov(
                    M.SourceSystem.VIRTUAL_INTERNSHIP, "group", row["group_id"], added
                ),
                group_key=row["group_id"],
                name=row["group_name"],
                track="AI Engineer",
            )
        )
        self.link(M.EdgeType.PART_OF_ROUND, grp, rnd)
        self.link(M.EdgeType.PART_OF_COHORT, rnd, cohort)

        learner = self.add(
            M.Learner(
                id=learner_uid("virtual_internship", row["learner_id"]),
                created_at=INGESTED_AT,
                provenance=self.prov(
                    M.SourceSystem.VIRTUAL_INTERNSHIP,
                    "learner",
                    row["learner_id"],
                    added,
                ),
                canonical_email=row["email"],
                display_name=row["name"],
                timezone=row.get("timezone"),
                learner_status=row.get("learner_status"),
            )
        )
        identity = self.add(
            M.LearnerIdentity(
                id=deterministic_id(
                    "virtual_internship", "learner_identity", row["learner_id"]
                ),
                created_at=INGESTED_AT,
                provenance=self.prov(
                    M.SourceSystem.VIRTUAL_INTERNSHIP,
                    "learner",
                    row["learner_id"],
                    added,
                ),
                source_learner_id=row["learner_id"],
                source_email=row["email"],
                source_display_name=row["name"],
                resolution_status=M.IdentityResolutionStatus.RESOLVED,
                resolution_method="exact_email",
                resolved_at=INGESTED_AT,
            )
        )
        self.link(M.EdgeType.IDENTIFIES, identity, learner)
        self.link(
            M.EdgeType.MEMBER_OF,
            learner,
            grp,
            role=row.get("role", "member"),
            added_at=added.isoformat(),
        )
        self._group = grp
        self._round = rnd
        return learner  # type: ignore[return-value]

    # ---- tasks, rubrics, LX ----------------------------------------------

    def build_tasks(self, learner: M.Learner) -> list[dict[str, Any]]:
        rows = [
            r
            for r in jsonl(self.dir / "lx_configs.jsonl")
            if r["learner_id"] == TARGET_LEARNER_ID
        ]

        # One task definition can back several LX rows; keep the richest rubric.
        best: dict[str, dict[str, Any]] = {}
        for r in rows:
            task = r["config_json"]["task"]
            key = task.get("task_definition_id") or r["lx_id"]
            scopes = len(task.get("rubric", {}).get("scopes", []))
            if key not in best or scopes > best[key]["_scopes"]:
                best[key] = {**r, "_scopes": scopes}

        project = self.add(
            M.Project(
                id=deterministic_id(
                    "virtual_internship", "project", "ai-video-generation-app"
                ),
                created_at=INGESTED_AT,
                provenance=self.prov(
                    M.SourceSystem.VIRTUAL_INTERNSHIP,
                    "project",
                    "ai-video-generation-app",
                    ts(rows[0]["activated_at"]) or INGESTED_AT,
                ),
                project_key="ai-video-generation-app",
                name="AI Video Generation App",
                description=(
                    "Team project: HTML/script generation pipeline rendered to "
                    "video."
                ),
                repository_url=redact(
                    "https://github.com/MoHatemTC/ai-video-generation-app"
                ),
            )
        )
        self._project = project
        self._tasks: dict[str, M.Task] = {}
        self._rubrics: dict[str, M.Rubric] = {}
        self._criteria: dict[str, M.RubricCriterion] = {}

        for key, r in best.items():
            task = r["config_json"]["task"]
            observed = ts(r["activated_at"]) or INGESTED_AT
            td = self.add(
                M.Task(
                    id=deterministic_id("virtual_internship", "task", key),
                    created_at=INGESTED_AT,
                    provenance=self.prov(
                        M.SourceSystem.VIRTUAL_INTERNSHIP,
                        "lx_config.task",
                        key,
                        observed,
                    ),
                    task_key=key,
                    headline=task.get("headline") or "untitled task",
                    description=task.get("description"),
                    task_archetype=r.get("task_archetype_id"),
                    technologies=task.get("technologies") or [],
                    deliverable_format=(task.get("deliverables") or {}).get("format"),
                    functional_requirements=task.get("functional_requirements") or [],
                    non_functional_requirements=task.get("non_functional_requirements")
                    or [],
                )
            )
            self._tasks[key] = td  # type: ignore[assignment]
            self.link(
                M.EdgeType.PART_OF_PROJECT,
                td,
                project,
                sprint_label=td.sprint_label,
                is_primary_deliverable=bool(td.technologies),
            )

            # Skills the task exercises, from its declared technologies.
            for tech in task.get("technologies") or []:
                for spec in match_skills(tech, limit=2):
                    self.link(M.EdgeType.REQUIRES_SKILL, td, self.skill(spec))

            rubric_src = task.get("rubric") or {}
            scopes = rubric_src.get("scopes") or []
            if scopes:
                rb = self.add(
                    M.Rubric(
                        id=deterministic_id("virtual_internship", "rubric", key),
                        created_at=INGESTED_AT,
                        provenance=self.prov(
                            M.SourceSystem.VIRTUAL_INTERNSHIP,
                            "lx_config.task.rubric",
                            key,
                            observed,
                        ),
                        rubric_key=key,
                        criterion_count=sum(
                            len(s.get("binary_points") or []) or 1 for s in scopes
                        ),
                    )
                )
                self._rubrics[key] = rb  # type: ignore[assignment]
                self.link(M.EdgeType.HAS_RUBRIC, td, rb)

                for scope in scopes:
                    points = scope.get("binary_points") or [{"id": scope.get("id")}]
                    for point in points:
                        ck = f"{key}:{scope.get('id')}:{point.get('id')}"
                        crit = self.add(
                            M.RubricCriterion(
                                id=deterministic_id(
                                    "virtual_internship", "rubric_criterion", ck
                                ),
                                created_at=INGESTED_AT,
                                provenance=self.prov(
                                    M.SourceSystem.VIRTUAL_INTERNSHIP,
                                    "lx_config.task.rubric.scope",
                                    key,
                                    observed,
                                    locator=f"scope:{scope.get('id')}/point:{point.get('id')}",
                                ),
                                criterion_key=ck,
                                scope_id=scope.get("id"),
                                point_id=point.get("id"),
                                category=scope.get("category"),
                                polarity=scope.get("polarity"),
                                requirement=scope.get("requirement"),
                                description=point.get("description")
                                or scope.get("description"),
                                evaluation_criteria=point.get("evaluation_criteria")
                                or point.get("quality"),
                            )
                        )
                        self._criteria[ck] = crit  # type: ignore[assignment]
                        self.link(M.EdgeType.HAS_CRITERION, rb, crit)
                        for spec in match_skills(
                            scope.get("requirement"),
                            point.get("description"),
                            point.get("evaluation_criteria"),
                        ):
                            self.link(M.EdgeType.TARGETS_SKILL, crit, self.skill(spec))

        # LX instances
        self._lx: dict[str, M.LearningExperience] = {}
        for r in rows:
            task = r["config_json"]["task"]
            key = task.get("task_definition_id") or r["lx_id"]
            observed = ts(r["activated_at"]) or INGESTED_AT
            lx = self.add(
                M.LearningExperience(
                    id=deterministic_id("virtual_internship", "lx", r["lx_id"]),
                    created_at=INGESTED_AT,
                    provenance=self.prov(
                        M.SourceSystem.VIRTUAL_INTERNSHIP,
                        "lx_config",
                        r["lx_id"],
                        observed,
                    ),
                    lx_key=r["lx_id"],
                    flow_id=r.get("flow_id"),
                    task_archetype_id=r.get("task_archetype_id"),
                    status=M.LXStatus(r["status"]),
                    outcome=M.LXOutcome(r["outcome"]) if r.get("outcome") else None,
                    trial_count=r.get("trial_count", 0),
                    extension_used=bool(r.get("extension_used")),
                    activated_at=ts(r.get("activated_at")),
                    deadline_at=ts(r.get("deadline_at")),
                    terminated_at=ts(r.get("terminated_at")),
                    terminated_reason=redact(r.get("terminated_reason")),
                    scenario_key=(
                        r["config_json"]
                        .get("lx_content", {})
                        .get("scenario", {})
                        .get("id")
                    ),
                    revision=r.get("revision"),
                )
            )
            self._lx[r["lx_id"]] = lx  # type: ignore[assignment]
            self.link(M.EdgeType.HAS_LEARNING_EXPERIENCE, learner, lx)
            if key in self._tasks:
                self.link(M.EdgeType.INSTANCE_OF, lx, self._tasks[key])
                if r.get("outcome") == "completed_success":
                    self.link(
                        M.EdgeType.COMPLETED_TASK,
                        learner,
                        self._tasks[key],
                        lx_key=r["lx_id"],
                        outcome=r["outcome"],
                        completed_at=(
                            ts(r.get("terminated_at")) or observed
                        ).isoformat(),
                        attempts=max(1, r.get("trial_count", 0) + 1),
                    )
        return rows

    # ---- interactions, submissions, grader results ------------------------

    _INTERESTING_TAGS = {
        "learner_submission",
        "grader_call",
        "feedback_delivered",
        "attempt_passed",
        "attempt_failed_retry",
        "attempt_failed_final",
        "misrouted_redirect",
        "human_help_requested",
        "deadline_extended",
        "task_kickoff",
    }

    def build_interactions_and_assessments(
        self, learner: M.Learner, lx_rows: list[dict[str, Any]]
    ) -> None:
        entries = [
            r
            for r in jsonl(self.dir / "interaction_logs.jsonl")
            if r["learner_id"] == TARGET_LEARNER_ID
        ]
        entries.sort(key=lambda r: r["entry"]["ts"])

        attempt_no: dict[str, int] = {}
        lx_outcome = {r["lx_id"]: r.get("outcome") for r in lx_rows}

        for row in entries:
            e = row["entry"]
            tags = set(e.get("tags") or [])
            if not (tags & self._INTERESTING_TAGS):
                continue
            occurred = ts(e["ts"]) or INGESTED_AT
            lx_key = row["lx_id"]
            lx = self._lx.get(lx_key)
            sid = f"{lx_key}:{row['entry_index']}"

            interaction = self.add(
                M.Interaction(
                    id=deterministic_id(
                        "virtual_internship", "interaction_log.entry", sid
                    ),
                    created_at=INGESTED_AT,
                    provenance=self.prov(
                        M.SourceSystem.VIRTUAL_INTERNSHIP,
                        "interaction_log.entry",
                        sid,
                        occurred,
                        locator=f"entry_index:{row['entry_index']}",
                    ),
                    interaction_kind=self._interaction_kind(tags),
                    tags=sorted(tags),
                    summary=redact(e.get("summary")),
                    trigger_node_id=e.get("trigger_node_id"),
                    occurred_at=occurred,
                    entry_index=row["entry_index"],
                    initiated_by=(
                        "learner"
                        if "learner_message" in tags or "learner_submission" in tags
                        else "system"
                    ),
                    carries_submission="submission" in e,
                    carries_feedback="feedback" in e,
                    message_count=len(e.get("actor_messages") or []),
                    participant_roles=sorted(
                        {
                            m.get("from")
                            for m in (e.get("actor_messages") or [])
                            if m.get("from")
                        }
                    ),
                    struggle_area=(e.get("struggle") or {}).get("area"),
                    struggle_resolved=(e.get("struggle") or {}).get("resolved"),
                )
            )
            self.link(
                M.EdgeType.PARTICIPATED_IN,
                learner,
                interaction,
                attendance="attended",
                role="learner",
            )
            if lx:
                days_in = None
                if lx.activated_at:
                    days_in = max(0, (occurred - lx.activated_at).days)
                self.link(
                    M.EdgeType.OCCURRED_IN,
                    interaction,
                    lx,
                    sequence_index=row["entry_index"],
                    days_into_lx=days_in,
                )

            if "feedback" not in e and "submission" not in e:
                continue

            # ---- attempt ------------------------------------------------
            attempt_no[lx_key] = attempt_no.get(lx_key, 0) + 1
            verdict = self._verdict(tags, (e.get("feedback") or {}).get("verdict"))
            attempt = self.add(
                M.Attempt(
                    id=deterministic_id(
                        "virtual_internship",
                        "attempt",
                        f"{lx_key}:{attempt_no[lx_key]}",
                    ),
                    created_at=INGESTED_AT,
                    provenance=self.prov(
                        M.SourceSystem.VIRTUAL_INTERNSHIP,
                        "interaction_log.attempt",
                        sid,
                        occurred,
                    ),
                    attempt_number=attempt_no[lx_key],
                    verdict=verdict,
                    submitted_at=occurred,
                    evaluated_at=occurred,
                )
            )
            if lx:
                self.link(M.EdgeType.HAS_ATTEMPT, lx, attempt)

            # ---- submission + artifacts ---------------------------------
            submission = None
            if "submission" in e:
                s = e["submission"]
                text = redact(s.get("text"))
                submission = self.add(
                    M.Submission(
                        id=deterministic_id("virtual_internship", "submission", sid),
                        created_at=INGESTED_AT,
                        provenance=self.prov(
                            M.SourceSystem.VIRTUAL_INTERNSHIP,
                            "interaction_log.submission",
                            sid,
                            occurred,
                            url=text if text and text.startswith("http") else None,
                        ),
                        kind=s.get("kind") or "unknown",
                        text=text,
                        attachment_count=len(s.get("attachments") or []),
                        attachment_names=[
                            redact(str(a.get("name") or a.get("filename") or a))[:120]
                            for a in (s.get("attachments") or [])
                            if isinstance(a, dict) or isinstance(a, str)
                        ][:10],
                        submission_url=(
                            text if text and text.startswith("http") else None
                        ),
                        submitted_at=occurred,
                        is_resubmission=attempt_no[lx_key] > 1,
                    )
                )
                self.link(
                    M.EdgeType.SUBMITTED,
                    learner,
                    submission,
                    submitted_at=occurred.isoformat(),
                    attempt_number=attempt_no[lx_key],
                    is_resubmission=attempt_no[lx_key] > 1,
                )
                self.link(
                    M.EdgeType.SUBMITTED_IN,
                    submission,
                    attempt,
                    attempt_number=attempt_no[lx_key],
                    is_final_attempt=verdict
                    in (M.AttemptVerdict.PASSED, M.AttemptVerdict.FAILED_FINAL),
                )

            if "feedback" not in e:
                continue

            # ---- assessment ---------------------------------------------
            fb = e["feedback"]
            tally = self._criterion_tally(fb)
            assessment = self.add(
                M.Assessment(
                    id=deterministic_id("assessment_engine", "grader_call", sid),
                    created_at=INGESTED_AT,
                    provenance=self.prov(
                        M.SourceSystem.ASSESSMENT_ENGINE,
                        "interaction_log.feedback",
                        sid,
                        occurred,
                    ),
                    assessment_kind="grader_call",
                    verdict=fb.get("verdict"),
                    summary=redact(fb.get("summary")),
                    mentor_reply=redact(fb.get("mentor_reply")),
                    criteria_total=tally["total"],
                    criteria_met=tally["Yes"],
                    criteria_partial=tally["Partial"],
                    criteria_unmet=tally["No"],
                    grader_version="grader@export",
                    evaluated_at=occurred,
                )
            )
            self.link(
                M.EdgeType.EVALUATED_BY,
                attempt,
                assessment,
                evaluated_at=occurred.isoformat(),
                verdict=verdict.value,
                is_final_evaluation=verdict
                in (M.AttemptVerdict.PASSED, M.AttemptVerdict.FAILED_FINAL),
            )

            task_key = next(
                (
                    r["config_json"]["task"].get("task_definition_id")
                    for r in lx_rows
                    if r["lx_id"] == lx_key
                ),
                None,
            )
            if task_key and task_key in self._rubrics:
                self.link(
                    M.EdgeType.USED_RUBRIC,
                    assessment,
                    self._rubrics[task_key],
                    rubric_version=self._rubrics[task_key].version,
                    criteria_evaluated=tally["total"],
                )

            self._evidence_from_grader(
                learner, assessment, submission, fb, occurred, task_key, sid
            )

            # ---- delivered-work evidence on a passing attempt ------------
            if verdict is M.AttemptVerdict.PASSED and submission is not None:
                self._delivered_work_evidence(
                    learner,
                    submission,
                    lx_key,
                    task_key,
                    occurred,
                    sid,
                    lx_outcome.get(lx_key),
                )

    @staticmethod
    def _interaction_kind(tags: set[str]) -> M.InteractionKind:
        for tag in (
            "learner_submission",
            "feedback_delivered",
            "task_kickoff",
            "misrouted_redirect",
            "human_mentor_message",
            "learner_message",
            "daily_check",
            "deadline_reminder",
            "scenario_event",
        ):
            if tag in tags:
                try:
                    return M.InteractionKind(tag)
                except ValueError:
                    break
        return M.InteractionKind.OTHER

    @staticmethod
    def _verdict(tags: set[str], raw: str | None) -> M.AttemptVerdict:
        if "attempt_passed" in tags or raw == "passed":
            return M.AttemptVerdict.PASSED
        if "attempt_failed_final" in tags:
            return M.AttemptVerdict.FAILED_FINAL
        if "attempt_failed_retry" in tags or raw == "failed_retry":
            return M.AttemptVerdict.FAILED_RETRY
        return M.AttemptVerdict.PENDING

    def _evidence_from_grader(
        self,
        learner: M.Learner,
        assessment: M.Assessment,
        submission: M.Submission | None,
        fb: dict[str, Any],
        occurred: datetime,
        task_key: str | None,
        sid: str,
    ) -> None:
        """Turn each rubric point the grader scored into one Evidence node.

        Only ``Yes`` and ``Partial`` results become evidence.  A ``No`` result
        is genuine counter-evidence and deserves its own model; representing it
        as ordinary evidence would let it be mistaken for support.  Deferred and
        documented rather than fudged.
        """
        scopes = self._parse_scope_results(fb.get("raw") or "")
        for scope in scopes:
            for point in scope.get("points") or []:
                status_raw = point.get("status")
                if status_raw not in ("Yes", "Partial"):
                    continue
                status = M.CriterionStatus(status_raw)
                conf = float(point.get("confidence_score") or 0.0)
                ck = f"{task_key}:{scope.get('id')}:{point.get('rubric_id')}"
                criterion = self._criteria.get(ck)

                ev = self.add(
                    M.Evidence(
                        id=evidence_uid(
                            "assessment_engine",
                            "rubric_point",
                            sid,
                            scope.get("id"),
                            point.get("rubric_id"),
                        ),
                        created_at=INGESTED_AT,
                        provenance=self.prov(
                            M.SourceSystem.ASSESSMENT_ENGINE,
                            "interaction_log.feedback.scope_point",
                            sid,
                            occurred,
                            locator=f"scope:{scope.get('id')}/rubric_point:{point.get('rubric_id')}",
                            method=M.ExtractionMethod.RULE_BASED,
                            evidence_type=M.EvidenceType.DIRECT_ASSESSMENT,
                        ),
                        evidence_type=M.EvidenceType.DIRECT_ASSESSMENT,
                        strength=(
                            M.EvidenceStrength.HIGH
                            if status is M.CriterionStatus.YES and conf >= 0.8
                            else (
                                M.EvidenceStrength.MEDIUM_HIGH
                                if conf >= 0.7
                                else M.EvidenceStrength.MEDIUM
                            )
                        ),
                        confidence=min(max(conf, 0.0), 1.0),
                        title=(
                            f"Rubric point {point.get('rubric_id')} scored "
                            f"'{status_raw}' "
                            f"({scope.get('category') or 'uncategorised'})"
                        ),
                        content=redact(
                            point.get("reason")
                            or point.get("evaluation_criteria")
                            or scope.get("requirement")
                            or "no grader reason recorded"
                        ),
                        observed_at=occurred,
                        access_scope=M.AccessScope.EMPLOYER_SHAREABLE,
                        criterion_status=status,
                    )
                )
                self.link(M.EdgeType.EVIDENCE_FOR_LEARNER, ev, learner)
                locator = (
                    f"scope:{scope.get('id')}/rubric_point:" f"{point.get('rubric_id')}"
                )
                self.link(
                    M.EdgeType.DERIVED_FROM,
                    ev,
                    assessment,
                    **self.evidence_tuple(ev),
                    source_locator=locator,
                    excerpt=(
                        redact(point.get("reason"))[:1000]
                        if point.get("reason")
                        else None
                    ),
                    extraction_confidence=min(max(conf, 0.0), 1.0),
                )
                if criterion is not None:
                    self.link(
                        M.EdgeType.DERIVED_FROM,
                        ev,
                        criterion,
                        **self.evidence_tuple(ev),
                        source_locator=locator,
                        extraction_confidence=min(max(conf, 0.0), 1.0),
                    )
                    self.link(
                        M.EdgeType.SCORED_CRITERION,
                        assessment,
                        criterion,
                        status=status_raw,
                        confidence=conf,
                        reason=redact(point.get("reason")),
                        artifact_keys=point.get("chunks_ids_met") or [],
                    )

                # Artifact chunks the grader actually cited.
                for chunk in (point.get("chunks_ids_met") or [])[:6]:
                    if submission is None:
                        break
                    art = self.add(
                        M.Artifact(
                            id=deterministic_id(
                                "virtual_internship", "artifact", f"{sid}:{chunk}"
                            ),
                            created_at=INGESTED_AT,
                            provenance=self.prov(
                                M.SourceSystem.VIRTUAL_INTERNSHIP,
                                "submission.chunk",
                                f"{sid}:{chunk}",
                                occurred,
                                locator=chunk,
                            ),
                            artifact_key=chunk,
                            path=chunk.rsplit("_", 1)[0],
                            artifact_type=self._artifact_type(chunk),
                        )
                    )
                    self.link(
                        M.EdgeType.CONTAINS_ARTIFACT,
                        submission,
                        art,
                        cited_by_grader=True,
                        citation_count=1,
                    )
                    self.link(
                        M.EdgeType.DERIVED_FROM,
                        ev,
                        art,
                        **self.evidence_tuple(ev),
                        source_locator=chunk,
                        extraction_confidence=min(max(conf, 0.0), 1.0),
                    )

                for spec in match_skills(
                    scope.get("requirement"),
                    point.get("reason"),
                    point.get("evaluation_criteria"),
                ):
                    self.link(M.EdgeType.EVIDENCE_ABOUT_SKILL, ev, self.skill(spec))
                    self.record_skill_evidence(
                        spec["slug"], M.SkillEvidenceTier.ASSESSED, ev
                    )

    def _delivered_work_evidence(
        self,
        learner: M.Learner,
        submission: M.Submission,
        lx_key: str,
        task_key: str | None,
        occurred: datetime,
        sid: str,
        outcome: str | None,
    ) -> None:
        td = self._tasks.get(task_key or "")
        if td is None:
            return
        techs = ", ".join(td.technologies) or "none recorded"
        ev = self.add(
            M.Evidence(
                id=evidence_uid("virtual_internship", "delivered_work", sid),
                created_at=INGESTED_AT,
                provenance=self.prov(
                    M.SourceSystem.VIRTUAL_INTERNSHIP,
                    "interaction_log.submission",
                    sid,
                    occurred,
                    url=submission.submission_url,
                    evidence_type=M.EvidenceType.DELIVERED_WORK,
                ),
                evidence_type=M.EvidenceType.DELIVERED_WORK,
                strength=M.EvidenceStrength.HIGH,
                confidence=0.9,
                title=f"Passed task: {td.headline}",
                content=(
                    f"Submission accepted on a passing attempt for '{td.headline}'. "
                    f"Task outcome: {outcome or 'unknown'}. "
                    f"Declared technologies: {techs}."
                ),
                observed_at=occurred,
                access_scope=M.AccessScope.EMPLOYER_SHAREABLE,
            )
        )
        self.link(M.EdgeType.EVIDENCE_FOR_LEARNER, ev, learner)
        self.link(
            M.EdgeType.DERIVED_FROM,
            ev,
            submission,
            **self.evidence_tuple(ev),
            source_locator=f"submission:{sid}",
            extraction_confidence=0.9,
        )
        for tech in td.technologies:
            for spec in match_skills(tech, limit=2):
                self.link(M.EdgeType.EVIDENCE_ABOUT_SKILL, ev, self.skill(spec))
                self.record_skill_evidence(
                    spec["slug"], M.SkillEvidenceTier.DEMONSTRATED, ev
                )

    @staticmethod
    def _artifact_type(chunk: str) -> str:
        low = chunk.lower()
        if low.endswith(tuple(f"{i}" for i in range(10))) and ".md_" in low:
            return "documentation"
        if ".diff" in low:
            return "diff"
        if any(x in low for x in (".py_", ".jsx_", ".sql_", ".ts_")):
            return "code"
        return "unknown"

    def _criterion_tally(self, fb: dict[str, Any]) -> dict[str, int]:
        """Count Yes / Partial / No across every rubric point the grader scored."""
        tally = {"total": 0, "Yes": 0, "Partial": 0, "No": 0}
        for scope in self._parse_scope_results(fb.get("raw") or ""):
            for point in scope.get("points") or []:
                status = point.get("status")
                if status in ("Yes", "Partial", "No"):
                    tally[status] += 1
                    tally["total"] += 1
        return tally

    @staticmethod
    def _parse_scope_results(raw: str) -> list[dict[str, Any]]:
        """Pull the JSON array out of the grader's semi-structured ``raw`` blob."""
        marker = "Scope Detailed Results:"
        if marker not in raw:
            return []
        tail = raw.split(marker, 1)[1].lstrip()
        decoder = json.JSONDecoder()
        try:
            value, _ = decoder.raw_decode(tail)
        except json.JSONDecodeError:
            return []
        return value if isinstance(value, list) else []

    # ---- delivered-work evidence from completed task instances ------------

    def build_delivered_work_from_outcomes(
        self, learner: M.Learner, lx_rows: list[dict[str, Any]]
    ) -> None:
        """A successfully closed task instance is delivered-work evidence.

        PRD 4.4 rates "delivered work" as high-strength evidence for
        *demonstrated execution*, which is a different claim from the grader's
        per-criterion score. Modelling both is what lets the DEMONSTRATED and
        ASSESSED tiers diverge - a learner can be assessed on a skill without
        ever shipping it, and vice versa.
        """
        for r in lx_rows:
            if r.get("outcome") != "completed_success":
                continue
            lx = self._lx.get(r["lx_id"])
            task_key = r["config_json"]["task"].get("task_definition_id")
            td = self._tasks.get(task_key or "")
            if lx is None or td is None:
                continue
            observed = (
                ts(r.get("terminated_at")) or ts(r.get("activated_at")) or INGESTED_AT
            )

            ev = self.add(
                M.Evidence(
                    id=evidence_uid("virtual_internship", "completed_lx", r["lx_id"]),
                    created_at=INGESTED_AT,
                    provenance=self.prov(
                        M.SourceSystem.VIRTUAL_INTERNSHIP,
                        "lx_config.outcome",
                        r["lx_id"],
                        observed,
                        method=M.ExtractionMethod.RULE_BASED,
                        evidence_type=M.EvidenceType.DELIVERED_WORK,
                    ),
                    evidence_type=M.EvidenceType.DELIVERED_WORK,
                    strength=M.EvidenceStrength.HIGH,
                    confidence=0.85,
                    title=f"Completed task instance: {td.headline}",
                    content=(
                        f"Task instance closed with outcome 'completed_success'. "
                        f"Task: '{td.headline}'. "
                        f"Declared technologies: "
                        f"{', '.join(td.technologies) or 'none recorded'}. "
                        f"Closing note: {redact(r.get('terminated_reason')) or 'none'}"
                    ),
                    observed_at=observed,
                    access_scope=M.AccessScope.EMPLOYER_SHAREABLE,
                )
            )
            self.link(M.EdgeType.EVIDENCE_FOR_LEARNER, ev, learner)
            self.link(
                M.EdgeType.DERIVED_FROM,
                ev,
                lx,
                **self.evidence_tuple(ev),
                source_locator=f"lx_outcome:{r['lx_id']}",
                extraction_confidence=0.85,
            )

            # Skills evidenced by shipping this task: the technologies it
            # declares, plus every skill its rubric explicitly targets. The
            # rubric is the stronger signal - most task definitions in the
            # export leave ``technologies`` empty but always carry a rubric.
            by_uid = {skill_uid(s2["slug"]): s2 for s2 in SKILL_REGISTRY}
            specs: list[dict[str, Any]] = []
            for tech in td.technologies:
                specs.extend(match_skills(tech, limit=2))

            criterion_ids = {
                c.id for k, c in self._criteria.items() if k.startswith(f"{task_key}:")
            }
            for edge in self.edges:
                hit = (
                    edge.type is M.EdgeType.REQUIRES_SKILL and edge.source_id == td.id
                ) or (
                    edge.type is M.EdgeType.TARGETS_SKILL
                    and edge.source_id in criterion_ids
                )
                if hit and edge.target_id in by_uid:
                    specs.append(by_uid[edge.target_id])

            seen: set[str] = set()
            for spec in specs:
                if spec["slug"] in seen:
                    continue
                seen.add(spec["slug"])
                self.link(M.EdgeType.EVIDENCE_ABOUT_SKILL, ev, self.skill(spec))
                self.record_skill_evidence(
                    spec["slug"], M.SkillEvidenceTier.DEMONSTRATED, ev
                )

    # ---- meetings, memory cards, behavioural observations -----------------

    #: metric_key prefix -> how to treat the card
    _BEHAVIOURAL_CATEGORY = {
        "behavioral_engagement.effort_signals": M.ObservationCategory.PROBLEM_SOLVING,
        "behavioral_engagement.engagement": M.ObservationCategory.COLLABORATION,
        "behavioral_engagement.adaptability": M.ObservationCategory.ADAPTABILITY,
        "behavioral_engagement.motivation_behavior": M.ObservationCategory.INITIATIVE,
        "behavioral_engagement.confidence_behavior": (
            M.ObservationCategory.COMMUNICATION
        ),
        "internship_context.current_blockers": M.ObservationCategory.HELP_SEEKING,
        "learning_goals.learner_tasks": M.ObservationCategory.INITIATIVE,
    }

    def build_meetings_and_observations(self, learner: M.Learner) -> None:
        meetings_by_id = {
            m["meeting_id"]: m for m in jsonl(self.dir / "meetings.jsonl")
        }
        cards = [
            c
            for c in jsonl(self.dir / "meeting_memory_cards.jsonl")
            if c["learner_id"] == TARGET_LEARNER_ID
        ]
        seen_meetings: dict[str, M.Meeting] = {}

        for card in cards:
            payload = card["normalized_payload"]
            meta = payload.get("project_metadata", {})
            observed = (
                ts(meta.get("scheduled_starts_at_utc"))
                or ts(payload.get("created_at"))
                or INGESTED_AT
            )
            mid = meta.get("scheduled_meeting_id") or card["meeting_id"]

            if mid not in seen_meetings:
                src = meetings_by_id.get(mid, {})
                meeting = self.add(
                    M.Meeting(
                        id=deterministic_id("meetings", "meeting", mid),
                        created_at=INGESTED_AT,
                        provenance=self.prov(
                            M.SourceSystem.MEETINGS,
                            "meeting",
                            mid,
                            observed,
                            locator=str(meta.get("zoom_meeting_uuid") or "")[:64]
                            or None,
                        ),
                        meeting_key=mid,
                        kind=M.MeetingKind(
                            src.get("kind") or meta.get("meeting_type") or "ad_hoc"
                        ),
                        topic=redact(src.get("topic") or meta.get("meeting_topic")),
                        starts_at_utc=ts(src.get("starts_at_utc")) or observed,
                        starts_at_local=src.get("starts_at_local"),
                        duration_min=src.get("duration_min"),
                        zoom_meeting_id=str(meta.get("zoom_meeting_id") or "") or None,
                        zoom_meeting_uuid=(
                            str(meta.get("zoom_meeting_uuid") or "")[:64] or None
                        ),
                        attendee_count=len(src.get("attendee_emails") or []) or None,
                        transcript_available=bool(meta.get("source_locator")),
                        extraction_status=src.get("extraction_status"),
                        extracted_at=ts(src.get("extracted_at")),
                        last_extraction_error=src.get("last_extraction_error"),
                    )
                )
                seen_meetings[mid] = meeting  # type: ignore[assignment]
                self.link(
                    M.EdgeType.HELD_FOR_GROUP,
                    meeting,
                    self._group,
                    round_key=self._round.round_key,
                    recurring=src.get("kind")
                    in ("standup", "sprint_planning", "retro"),
                )
                self.link(
                    M.EdgeType.PARTICIPATED_IN,
                    learner,
                    meeting,
                    attendance="attended",
                    role="learner",
                )
            meeting = seen_meetings[mid]

            metric = card["metric_key"]
            content = redact(payload.get("content")) or ""
            rationale = redact(payload.get("rationale"))
            excerpt = redact(card.get("response_excerpt"))
            conf = float(meta.get("confidence") or 0.5)

            # -- evidence node ------------------------------------------------
            # A learner describing their own stack in a standup is self-reported,
            # not demonstrated. Typing it honestly is what keeps the DECLARED and
            # DEMONSTRATED tiers meaningfully different.
            is_tech_claim = metric == "internship_context.tech_stack"
            card_evidence_type = (
                M.EvidenceType.SELF_DECLARED
                if is_tech_claim
                else M.EvidenceType.OBSERVED_BEHAVIOR
            )
            ev = self.add(
                M.Evidence(
                    id=evidence_uid("meeting_memory", "memory_card", card["card_id"]),
                    created_at=INGESTED_AT,
                    provenance=self.prov(
                        M.SourceSystem.MEETING_MEMORY,
                        "meeting_memory_card",
                        card["card_id"],
                        observed,
                        locator=meta.get("source_locator"),
                        method=M.ExtractionMethod.LLM_EXTRACTION,
                        evidence_type=card_evidence_type,
                    ),
                    evidence_type=card_evidence_type,
                    strength=(
                        M.EvidenceStrength.LOW
                        if is_tech_claim
                        else M.EvidenceStrength.MEDIUM
                    ),
                    confidence=conf,
                    title=f"{metric} ({meta.get('meeting_type') or 'meeting'})",
                    content=content or (excerpt or "no content recorded"),
                    observed_at=observed,
                    access_scope=M.AccessScope.EMPLOYER_SHAREABLE,
                )
            )
            self.link(M.EdgeType.EVIDENCE_FOR_LEARNER, ev, learner)
            self.link(
                M.EdgeType.DERIVED_FROM,
                ev,
                meeting,
                **self.evidence_tuple(ev),
                source_locator=meta.get("source_locator"),
                excerpt=(excerpt or content or None),
                extraction_confidence=conf,
            )

            if is_tech_claim:
                for spec in match_skills(content, limit=3):
                    self.link(M.EdgeType.EVIDENCE_ABOUT_SKILL, ev, self.skill(spec))
                    self.record_skill_evidence(
                        spec["slug"], M.SkillEvidenceTier.DECLARED, ev
                    )

            # -- behavioural observation --------------------------------------
            category = self._BEHAVIOURAL_CATEGORY.get(metric)
            if category is None or not content:
                continue
            obs = self.add(
                M.Observation(
                    id=observation_uid(learner.id, "meeting_memory", card["card_id"]),
                    created_at=INGESTED_AT,
                    computed_at=INGESTED_AT,
                    computed_by=BUILDER,
                    derivation_note=f"derived from memory card metric '{metric}'",
                    category=category,
                    context=(
                        f"{meta.get('meeting_type') or 'meeting'} on "
                        f"{observed.date().isoformat()}"
                        + (
                            f" - {meta.get('meeting_topic')}"
                            if meta.get("meeting_topic")
                            else ""
                        )
                    ),
                    behavior=content,
                    outcome=rationale,
                    observed_at=observed,
                    confidence=conf,
                )
            )
            self.link(M.EdgeType.HAS_OBSERVATION, learner, obs)
            self.link(
                M.EdgeType.OBSERVED_IN,
                obs,
                meeting,
                source_locator=meta.get("source_locator"),
                excerpt=(excerpt or None),
            )
            self.link(M.EdgeType.SUPPORTED_BY_EVIDENCE, obs, ev)

    # ---- derived skill assertions -----------------------------------------

    def build_skill_assertions(self, learner: M.Learner) -> None:
        for slug, tiers in sorted(self.skill_evidence.items()):
            skill = self.skill_nodes[slug]
            for tier, items in sorted(tiers.items(), key=lambda kv: kv[0].value):
                uniq = {e.id: e for e in items}
                evidence = sorted(uniq.values(), key=lambda e: e.observed_at)
                sources = {e.provenance.source_system for e in evidence}
                status = self._grade(len(evidence), len(sources), tier)
                assertion = self.add(
                    M.SkillAssertion(
                        id=assertion_uid(learner.id, skill.id, tier.value),
                        created_at=INGESTED_AT,
                        computed_at=INGESTED_AT,
                        computed_by="skill-aggregator@0.1.0",
                        derivation_note=(
                            "seed aggregation; Sprint 2 replaces this "
                            "with the real aggregation service"
                        ),
                        tier=tier,
                        status=status,
                        confidence=round(
                            sum(e.confidence for e in evidence) / len(evidence), 3
                        ),
                        evidence_count=len(evidence),
                        evidence_source_count=len(sources),
                        first_evidence_at=evidence[0].observed_at,
                        latest_evidence_at=evidence[-1].observed_at,
                        rationale=(
                            f"{len(evidence)} {tier.value} evidence item(s) from "
                            f"{len(sources)} source system(s): "
                            f"{', '.join(sorted(s.value for s in sources))}."
                        ),
                    )
                )
                self.link(M.EdgeType.HAS_SKILL_ASSERTION, learner, assertion)
                self.link(M.EdgeType.ABOUT_SKILL, assertion, skill)
                for ev in evidence:
                    self.link(M.EdgeType.SUPPORTED_BY_EVIDENCE, assertion, ev)

                tier_edge = {
                    M.SkillEvidenceTier.DECLARED: M.EdgeType.DECLARED_SKILL,
                    M.SkillEvidenceTier.EXPOSED: M.EdgeType.EXPOSED_TO_SKILL,
                    M.SkillEvidenceTier.ASSESSED: M.EdgeType.ASSESSED_ON_SKILL,
                    M.SkillEvidenceTier.DEMONSTRATED: M.EdgeType.DEMONSTRATED_SKILL,
                }[tier]
                self.link(
                    tier_edge,
                    learner,
                    skill,
                    assertion_id=str(assertion.id),
                    status=status.value,
                    confidence=assertion.confidence,
                    evidence_count=assertion.evidence_count,
                    latest_evidence_at=evidence[-1].observed_at.isoformat(),
                )

    @staticmethod
    def _grade(
        count: int, sources: int, tier: M.SkillEvidenceTier
    ) -> M.AssertionStatus:
        """Deliberately conservative banding.

        Evidence *diversity* is required for STRONG: five grader points from a
        single assessment is one opinion repeated, not five independent proofs.
        This is the PRD 8.2 guard against a heavily-observed learner looking
        stronger purely because more was logged about them.
        """
        if tier is M.SkillEvidenceTier.DECLARED:
            return M.AssertionStatus.WEAK
        if count >= 3 and sources >= 2:
            return M.AssertionStatus.STRONG
        if count >= 2:
            return M.AssertionStatus.MODERATE
        return M.AssertionStatus.WEAK

    # ---- career goal + the deliberate evidence gap -------------------------

    #: Target competencies for the enrolled track. Derived from the group the
    #: learner is actually in ("G2 - AI Engineer Internship"), so the goal is
    #: itself traceable rather than invented.
    _TARGET_COMPETENCIES = [
        "python",
        "fastapi",
        "rest-api",
        "llm",
        "prompt-engineering",
        "docker",
    ]

    def build_career_goal(self, learner: M.Learner) -> None:
        goal = self.add(
            M.CareerGoal(
                id=deterministic_id("profile", "career_goal", str(learner.id)),
                created_at=INGESTED_AT,
                provenance=self.prov(
                    M.SourceSystem.PROFILE,
                    "track_enrollment",
                    self._group.group_key,
                    INGESTED_AT,
                    method=M.ExtractionMethod.RULE_BASED,
                ),
                status=M.CareerGoalStatus.STATED,
                target_role="AI Engineer",
                stated_at=INGESTED_AT,
                notes="Derived from enrolled track 'G2 - AI Engineer Internship'. "
                "No explicit learner-stated goal exists in the source export; "
                "replace with a learner-confirmed goal when the profile service ships.",
            )
        )
        self.link(M.EdgeType.HAS_CAREER_GOAL, learner, goal)

        docker = {
            "name": "Docker",
            "slug": "docker",
            "category": M.SkillCategory.DIGITAL_AI_SKILLS,
            "aliases": ["containerisation", "containerization", "container"],
        }
        for slug in self._TARGET_COMPETENCIES:
            spec = next(
                (s for s in SKILL_REGISTRY if s["slug"] == slug),
                docker if slug == "docker" else None,
            )
            if spec is None:
                continue
            self.link(M.EdgeType.GOAL_TARGETS_SKILL, goal, self.skill(spec))

        # The point of the whole product: a target competency with NO evidence.
        # This assertion is what Epic 3 turns into a validation scenario, and it
        # is only expressible because "no evidence" is a first-class state.
        docker_skill = self.skill(docker)
        gap = self.add(
            M.SkillAssertion(
                id=assertion_uid(
                    learner.id, docker_skill.id, M.SkillEvidenceTier.DEMONSTRATED.value
                ),
                created_at=INGESTED_AT,
                computed_at=INGESTED_AT,
                computed_by="skill-aggregator@0.1.0",
                tier=M.SkillEvidenceTier.DEMONSTRATED,
                status=M.AssertionStatus.NO_EVIDENCE,
                confidence=0.0,
                evidence_count=0,
                evidence_source_count=0,
                rationale=(
                    "Docker is a target competency for the AI Engineer track "
                    "but no evidence of any tier was found across LMS, "
                    "internship, assessment or meeting sources. This is an "
                    "evidence gap, not a demonstrated absence of skill - "
                    "Epic 3 should raise a validation scenario."
                ),
            )
        )
        self.link(M.EdgeType.HAS_SKILL_ASSERTION, learner, gap)
        self.link(M.EdgeType.ABOUT_SKILL, gap, docker_skill)

    # ---- employer authorisation stub --------------------------------------

    def build_employer_access(self) -> None:
        employer = self.add(
            M.Employer(
                id=deterministic_id("profile", "employer", "demo-employer"),
                created_at=INGESTED_AT,
                provenance=self.prov(
                    M.SourceSystem.PROFILE, "employer", "demo-employer", INGESTED_AT
                ),
                employer_key="demo-employer",
                name="Demo Employer (pilot)",
            )
        )
        grant = self.add(
            M.AccessGrant(
                id=deterministic_id("profile", "access_grant", "demo-employer:round2"),
                created_at=INGESTED_AT,
                provenance=self.prov(
                    M.SourceSystem.PROFILE,
                    "access_grant",
                    "demo-employer:round2",
                    INGESTED_AT,
                ),
                grant_key="demo-employer:round2",
                granted_at=INGESTED_AT,
                allowed_evidence_types=[
                    M.EvidenceType.DIRECT_ASSESSMENT,
                    M.EvidenceType.DELIVERED_WORK,
                    M.EvidenceType.OBSERVED_BEHAVIOR,
                ],
                allowed_access_scopes=[M.AccessScope.EMPLOYER_SHAREABLE],
            )
        )
        self.link(M.EdgeType.HAS_ACCESS_GRANT, employer, grant)
        self.link(M.EdgeType.GRANTS_ACCESS_TO, grant, self._round)


# ===========================================================================


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--logs-dir",
        required=True,
        type=Path,
        help="path to '<export>/group-a-ai-engineer'",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent.parent
        / "tests"
        / "fixtures"
        / "sample_learner_seed.json",
    )
    args = ap.parse_args()

    graph = SeedBuilder(args.logs_dir).build()
    args.out.write_text(
        graph.model_dump_json(indent=2, exclude_none=True) + "\n", encoding="utf-8"
    )

    print(f"wrote {args.out.name}")
    print(f"  nodes: {len(graph.nodes)}   edges: {len(graph.edges)}")
    for label, n in graph.counts().items():
        print(f"    {label:20} {n}")


if __name__ == "__main__":
    main()
