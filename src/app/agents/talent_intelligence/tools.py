import json as _json
import re
from typing import Any

from src.app.core import TAXONOMY_TAG_DESCRIPTIONS
from src.app.graph.connections import get_driver
from src.app.schemas.models import ToolResult


def _run(cypher: str, **params: Any) -> list[dict[str, Any]]:
    try:
        with get_driver().session() as session:
            result = session.run(cypher, **params)
            return [dict(record) for record in result]
    except Exception:
        return []


def _find_learner(learner_query: str) -> dict[str, Any] | None:
    query = learner_query.strip().lower()
    if not query:
        return None
    rows = _run(
        """
        MATCH (l:LearnerProfile)
        WHERE toLower(l.learner_id) = $q
           OR toLower(l.name)       = $q
        RETURN
            l.learner_id    AS learner_id,
            l.name          AS name,
            l.role          AS role,
            l.group_name    AS group_name,
            l.round_name    AS round_name,
            l.learner_status AS learner_status,
            l.added_at      AS added_at
        LIMIT 1
        """,
        q=query,
    )
    if rows:
        return rows[0]

    normalized = query.replace("-", " ").replace("_", " ")
    parts = normalized.split()
    core_parts = [p for p in parts if p not in {"learner", "leraner", "student"}]
    core_id = " ".join(core_parts) if core_parts else normalized
    full_candidate = f"learner {core_id}"

    rows = _run(
        """
        MATCH (l:LearnerProfile)
        WHERE toLower(l.learner_id) = $core_id
           OR toLower(l.name) = $full_candidate
           OR toLower(l.name) = 'learner ' + $core_id
           OR toLower(replace(replace(l.name, '-', ' '), '_', ' ')) = $normalized
           OR toLower(l.name) ENDS WITH (' ' + $core_id)
        RETURN
            l.learner_id    AS learner_id,
            l.name          AS name,
            l.role          AS role,
            l.group_name    AS group_name,
            l.round_name    AS round_name,
            l.learner_status AS learner_status,
            l.added_at      AS added_at
        LIMIT 1
        """,
        core_id=core_id,
        full_candidate=full_candidate,
        normalized=normalized,
    )
    return rows[0] if rows else None


def _card_row_to_evidence(row: dict[str, Any]) -> dict[str, Any]:
    tags = row.get("tags") or []
    if isinstance(tags, str):
        try:
            tags = _json.loads(tags)
        except Exception:
            tags = []

    source_ref = (
        row.get("source_ref")
        or row.get("meeting_id")
        or row.get("task_ref")
        or row.get("lx_id")
        or row.get("source_datasource_id")
        or row.get("source_id")
    )
    source_type = row.get("source_type") or (
        "meeting_transcript" if row.get("meeting_id") else "memory_card"
    )

    return {
        "evidence_id": row.get("evidence_id") or row.get("card_id"),
        "learner_id": row.get("learner_id"),
        "source_type": source_type,
        "source_ref": source_ref,
        "date": (
            str(row["date"])
            if row.get("date")
            else (str(row["created_at"]) if row.get("created_at") else None)
        ),
        "observation": row.get("observation")
        or row.get("content")
        or (
            row.get("normalized_payload", {}).get("content", "")
            if isinstance(row.get("normalized_payload"), dict)
            else ""
        ),
        "context": row.get("context") or row.get("metric_key", ""),
        "tags": list(tags),
        "metric_key": row.get("metric_key"),
        "rationale": row.get("rationale", ""),
    }


def _memory_card_rows(
    learner_id: str, where_clause: str = "", **params: Any
) -> list[dict[str, Any]]:
    rows = _run(
        f"""
        MATCH (l:LearnerProfile {{learner_id: $learner_id}})
            -[:HAS_MEMORY_CARD]->(m:MemoryCard)
        OPTIONAL MATCH (ds:DataSource)-[:EXTRACTED_INTO]->(m)
        {where_clause}
        RETURN
            m.card_id    AS evidence_id,
            m.metric_key AS metric_key,
            m.content    AS observation,
            m.rationale  AS rationale,
            m.tags       AS tags,
            m.created_at AS date,
            $learner_id  AS learner_id,
            coalesce(m.source_ref, m.meeting_id, m.lx_id, ds.datasource_id, null)
                AS source_ref,
            coalesce(ds.datasource_name, 'meeting_transcript') AS source_type
        ORDER BY m.created_at DESC
        """,
        learner_id=learner_id,
        **params,
    )
    return rows


def get_learner_profile(learner_query: str) -> ToolResult:
    learner = _find_learner(learner_query)
    if learner is None:
        return ToolResult("not_found", None, "Learner not found.")

    learner_id = learner["learner_id"]

    coverage_rows = _run(
        """
        MATCH (l:LearnerProfile {learner_id: $learner_id})
            -[:HAS_MEMORY_CARD]->(m:MemoryCard)
        OPTIONAL MATCH (ds:DataSource)-[:EXTRACTED_INTO]->(m)
        RETURN
            count(m)           AS evidence_count,
            max(m.created_at)  AS most_recent_evidence_date,
            collect(
                DISTINCT coalesce(
                    ds.datasource_name, 'meeting_transcript', 'memory_card'
                )
            ) AS source_types
        """,
        learner_id=learner_id,
    )
    cov = coverage_rows[0] if coverage_rows else {}

    profile = {
        "learner_id": learner_id,
        "name": learner.get("name"),
        "role": learner.get("role"),
        "group_name": learner.get("group_name"),
        "round_name": learner.get("round_name"),
        "learner_status": learner.get("learner_status"),
        "evidence_coverage": {
            "evidence_count": cov.get("evidence_count", 0),
            "most_recent_evidence_date": (
                str(cov["most_recent_evidence_date"])
                if cov.get("most_recent_evidence_date")
                else None
            ),
            "source_types": sorted(
                list(st)
                if isinstance(st := cov.get("source_types"), (list, set, tuple))
                else []
            ),
        },
    }
    return ToolResult("ok", profile, "")


def compare_learners(
    first_learner_query: str,
    second_learner_query: str,
    focus: str = "",
) -> ToolResult:
    """Compare two learners using evidence coverage, never a suitability score."""
    queries = [first_learner_query.strip(), second_learner_query.strip()]
    if not all(queries):
        return ToolResult(
            "insufficient_evidence",
            [],
            "Two learner names or IDs are required for comparison.",
        )

    learners = [_find_learner(query) for query in queries]
    missing = [
        query
        for query, learner in zip(queries, learners, strict=True)
        if learner is None
    ]
    if missing:
        return ToolResult(
            "not_found",
            [],
            f"Learner not found: {', '.join(missing)}.",
        )

    compared: list[dict[str, Any]] = []
    normalized_focus = focus.strip()
    for learner in learners:
        assert learner is not None
        learner_id = str(learner["learner_id"])
        profile = get_learner_profile(learner_id)
        evidence = search_evidence(
            learner_id,
            query=normalized_focus,
            limit=20,
        )
        compared.append(
            {
                "learner_id": learner_id,
                "name": learner.get("name"),
                "role": learner.get("role"),
                "evidence_coverage": (
                    profile.data.get("evidence_coverage", {})
                    if profile.status == "ok" and isinstance(profile.data, dict)
                    else {}
                ),
                "evidence_status": evidence.status,
                "evidence": evidence.data if isinstance(evidence.data, list) else [],
            }
        )

    return ToolResult(
        "ok",
        {
            "focus": normalized_focus or "all available evidence",
            "learners": compared,
            "limitations": [
                "Evidence coverage is not a proficiency score or hiring ranking.",
                "Missing evidence does not mean the learner lacks the skill.",
            ],
        },
        "",
    )


def get_skill_proofs(learner_id: str, skill: str) -> ToolResult:
    normalized = skill.strip().lower()
    rows = _memory_card_rows(
        learner_id,
        """
        WHERE (toLower(m.content) CONTAINS $skill
               OR toLower(m.metric_key) CONTAINS $skill)
          AND m.metric_key <> 'learning_goals.learner_tasks'
        """,
        skill=normalized,
    )
    evidence = [_card_row_to_evidence(r) for r in rows]
    if not evidence:
        return ToolResult(
            "insufficient_evidence", [], "No matching skill evidence was found."
        )
    return ToolResult("ok", evidence, "")


def search_evidence(
    learner_id: str,
    query: str = "",
    source_type: str = "",
    start_date: str = "",
    end_date: str = "",
    limit: int = 100,
) -> ToolResult:
    """Search attributable evidence with optional source and date filters."""
    normalized_query = query.strip().lower()
    normalized_source = source_type.strip().lower()
    result_limit = max(1, min(limit, 100))
    rows = _run(
        """
        MATCH (l:LearnerProfile {learner_id: $learner_id})
        OPTIONAL MATCH (l)-[:HAS_MEMORY_CARD]->(direct:MemoryCard)
        OPTIONAL MATCH (l)-[:PRODUCED]->(:DataSource)-[:EXTRACTED_INTO]->
            (derived:MemoryCard)
        WITH collect(DISTINCT direct) + collect(DISTINCT derived) AS cards
        UNWIND cards AS m
        WITH DISTINCT m
        OPTIONAL MATCH (ds:DataSource)-[:EXTRACTED_INTO]->(m)
        WITH m, collect(ds.datasource_name) AS source_names,
             collect(ds.datasource_id) AS source_ids
        WHERE m IS NOT NULL
          AND ($query = '' OR toLower(coalesce(m.content, '')) CONTAINS $query
               OR toLower(coalesce(m.metric_key, '')) CONTAINS $query
               OR any(tag IN coalesce(m.tags, []) WHERE toLower(tag) CONTAINS $query))
            AND ($source_type = '' OR toLower(coalesce(
                head(source_names), 'memory_card')) = $source_type)
          AND ($start_date = '' OR toString(coalesce(m.created_at, '')) >= $start_date)
          AND ($end_date = '' OR toString(coalesce(m.created_at, '')) <= $end_date)
        RETURN
            m.card_id AS evidence_id,
            m.metric_key AS metric_key,
            m.content AS observation,
            m.rationale AS rationale,
            m.tags AS tags,
            m.created_at AS date,
            $learner_id AS learner_id,
            coalesce(m.source_ref, m.meeting_id, m.lx_id, head(source_ids), null)
                AS source_ref,
            coalesce(head(source_names), 'memory_card') AS source_type
        ORDER BY m.created_at DESC
        LIMIT $limit
        """,
        learner_id=learner_id,
        query=normalized_query,
        source_type=normalized_source,
        start_date=start_date.strip(),
        end_date=end_date.strip(),
        limit=result_limit,
    )
    evidence = [_card_row_to_evidence(row) for row in rows]
    if not evidence:
        return ToolResult(
            "insufficient_evidence", [], "No matching evidence was found."
        )
    return ToolResult("ok", evidence, "")


def get_review_outcomes(learner_id: str) -> ToolResult:
    """Retrieve learner submissions, verdicts, feedback, and rubric outcomes."""
    rows = _run(
        """
        MATCH (l:LearnerProfile {learner_id: $learner_id})-[:PRODUCED]->(ds:DataSource)
        WHERE ds.datasource_name = 'review'
        RETURN ds.datasource_id AS event_id, ds.timestamp AS date,
               ds.payload_json AS payload_json
        ORDER BY ds.timestamp DESC
        """,
        learner_id=learner_id,
    )
    outcomes: list[dict[str, Any]] = []
    for row in rows:
        payload = _parse_payload(row.get("payload_json"))
        outcomes.append(
            {
                "event_id": row.get("event_id"),
                "date": str(row["date"]) if row.get("date") else None,
                "source_type": "review",
                "lx_id": payload.get("lx_id"),
                "task_headline": payload.get("task_headline"),
                "attempt_number": payload.get("attempt_number"),
                "verdict": payload.get("verdict"),
                "submission_text": payload.get("submission_text"),
                "feedback_summary": payload.get("feedback_summary"),
                "mentor_reply": payload.get("mentor_reply"),
                "detailed_rubric_evaluations": payload.get(
                    "detailed_rubric_evaluations", []
                ),
            }
        )
    if not outcomes:
        return ToolResult("insufficient_evidence", [], "No review outcomes were found.")
    return ToolResult("ok", outcomes, "")


def get_assessment_results(learner_id: str) -> ToolResult:
    """Retrieve learner assessment scores and question-level results."""
    rows = _run(
        """
        MATCH (l:LearnerProfile {learner_id: $learner_id})-[:PRODUCED]->(ds:DataSource)
        WHERE ds.datasource_name IN ['assessments', 'assesments']
        RETURN ds.datasource_id AS event_id, ds.timestamp AS date,
               ds.payload_json AS payload_json
        ORDER BY ds.timestamp DESC
        """,
        learner_id=learner_id,
    )
    assessments: list[dict[str, Any]] = []
    for row in rows:
        payload = _parse_payload(row.get("payload_json"))
        assessments.append(
            {
                "event_id": row.get("event_id"),
                "date": str(row["date"]) if row.get("date") else None,
                "source_type": "assessment",
                "lx_id": payload.get("lx_id"),
                "assessment_type": payload.get("assessment_type"),
                "topic_id": payload.get("topic_id"),
                "score": payload.get("score"),
                "max_score": payload.get("max_score"),
                "answers": payload.get("answers", []),
            }
        )
    if not assessments:
        return ToolResult(
            "insufficient_evidence", [], "No assessment results were found."
        )
    return ToolResult("ok", assessments, "")


def _parse_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            payload = _json.loads(value)
        except (TypeError, ValueError):
            return {}
        return payload if isinstance(payload, dict) else {}
    return {}


def find_learners_with_skill(skill: str) -> ToolResult:
    normalized = skill.strip().lower()
    if not normalized:
        return ToolResult("insufficient_evidence", [], "A skill is required.")

    rows = _run(
        """
        MATCH (l:LearnerProfile)-[:HAS_MEMORY_CARD]->(m:MemoryCard)
        WHERE toLower(m.content) CONTAINS $skill
           OR toLower(m.metric_key) CONTAINS $skill
        RETURN
            l.learner_id AS learner_id,
            l.name AS name,
            m.card_id AS evidence_id,
            m.metric_key AS metric_key,
            m.content AS observation,
            m.tags AS tags,
            m.created_at AS date,
            'memory_card' AS source_type
        ORDER BY m.created_at DESC
        LIMIT 500
        """,
        skill=normalized,
    )
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        learner_id = row.get("learner_id")
        if not learner_id:
            continue
        learner = grouped.setdefault(
            learner_id,
            {
                "learner_id": learner_id,
                "name": row.get("name"),
                "evidence": [],
            },
        )
        learner["evidence"].append(_card_row_to_evidence(row))

    results = []
    for learner in grouped.values():
        evidence = learner["evidence"]
        learner["evidence_count"] = len(evidence)
        learner["most_recent_date"] = evidence[0].get("date")
        results.append(learner)
    results.sort(
        key=lambda learner: (
            -learner["evidence_count"],
            learner["most_recent_date"] or "",
            learner["name"] or "",
        ),
    )
    if not results:
        return ToolResult(
            "insufficient_evidence",
            [],
            f"No learner evidence was found for {normalized}.",
        )
    return ToolResult("ok", results, "")


def get_behavioral_context(learner_id: str) -> ToolResult:
    taxonomy_tags = list(TAXONOMY_TAG_DESCRIPTIONS)
    rows = _memory_card_rows(
        learner_id,
        """
        WHERE any(tag IN coalesce(m.tags, []) WHERE tag IN $taxonomy_tags)
        """,
        taxonomy_tags=taxonomy_tags,
    )
    evidence = [_card_row_to_evidence(r) for r in rows]
    if not evidence:
        return ToolResult(
            "insufficient_evidence", [], "No behavioral observations were found."
        )
    return ToolResult("ok", evidence, "")


def get_strengths_and_gaps(learner_id: str) -> ToolResult:
    taxonomy_tags = list(TAXONOMY_TAG_DESCRIPTIONS)
    rows = _run(
        """
        MATCH (l:LearnerProfile {learner_id: $learner_id})
            -[:HAS_MEMORY_CARD]->(m:MemoryCard)
        WHERE any(tag IN coalesce(m.tags, []) WHERE tag IN $taxonomy_tags)
        RETURN
            m.card_id    AS evidence_id,
            m.metric_key AS metric_key,
            m.content    AS observation,
            m.tags       AS tags,
            m.created_at AS date,
            'memory_card' AS source_type
        """,
        learner_id=learner_id,
        taxonomy_tags=taxonomy_tags,
    )

    if not rows:
        return ToolResult(
            "not_found",
            {"strengths": [], "gaps": []},
            "Learner has no evidence records.",
        )

    _POSITIVE = re.compile(
        r"\b(?:demonstrated|successfully|helped|resolved|adapted)\b",
        re.IGNORECASE,
    )
    _NEGATIVE = re.compile(
        r"\b(?:not|never|failed|unable|struggled|lack\w*)\b",
        re.IGNORECASE,
    )
    strengths = []
    present: set[str] = set()
    for row in rows:
        tags = row.get("tags") or []
        for tag in tags:
            if tag not in TAXONOMY_TAG_DESCRIPTIONS:
                continue
            present.add(tag)
            if _POSITIVE.search(row.get("observation", "")) and not _NEGATIVE.search(
                row.get("observation", "")
            ):
                strengths.append(
                    {
                        "area": tag,
                        "evidence_ids": [row["evidence_id"]],
                        "most_recent_date": (
                            str(row["date"]) if row.get("date") else None
                        ),
                        "observation": row["observation"],
                        "source_type": row["source_type"],
                    }
                )
    gaps = [
        {
            "area": area,
            "status": "insufficient_evidence",
            "reason": "No matching observation was found in the graph.",
        }
        for area in sorted(set(TAXONOMY_TAG_DESCRIPTIONS) - present)
    ]
    return ToolResult("ok", {"strengths": strengths, "gaps": gaps}, "")


def get_milestone_history(learner_id: str) -> ToolResult:
    outcome_tags = [
        "learner_submission",
        "feedback_delivered",
        "grader_call",
        "attempt_passed",
        "task_closed",
        "lx_ended_success",
    ]
    rows = _run(
        """
        MATCH (l:LearnerProfile {learner_id: $learner_id})-[:PRODUCED]->(ds:DataSource)
        WHERE ds.datasource_name IN ['review', 'assessments']
          AND any(tag IN ds.tags WHERE tag IN $outcome_tags)
        RETURN
            ds.datasource_id   AS event_id,
            ds.timestamp       AS date,
            ds.datasource_name AS source_type,
            ds.payload_json    AS payload_json
        ORDER BY ds.timestamp ASC
        """,
        learner_id=learner_id,
        outcome_tags=outcome_tags,
    )

    milestones: list[dict[str, Any]] = []
    for row in rows:
        payload = _parse_payload(row.get("payload_json"))
        verdict = payload.get("verdict", "")
        summary = (
            payload.get("task_headline")
            or payload.get("assessment_type")
            or row["source_type"]
        )
        milestones.append(
            {
                "event_id": row["event_id"],
                "date": str(row["date"]) if row.get("date") else None,
                "summary": f"{summary} — {verdict}" if verdict else summary,
                "tags": [verdict] if verdict else [],
                "source_type": row["source_type"],
                "context": "LX workflow event",
            }
        )

    if not milestones:
        return ToolResult(
            "insufficient_evidence", [], "No milestone history was found."
        )
    return ToolResult("ok", milestones, "")


def investigate_employer(learner_id: str, focus: str = "") -> ToolResult:

    normalized_focus = focus.strip().lower()
    rows = _run(
        """
        MATCH (l:LearnerProfile {learner_id: $learner_id})
        OPTIONAL MATCH (l)-[:HAS_MEMORY_CARD]->(direct:MemoryCard)
        OPTIONAL MATCH (l)-[:PRODUCED]->(:DataSource)-[:EXTRACTED_INTO]->
            (derived:MemoryCard)
        WITH l, collect(DISTINCT direct) + collect(DISTINCT derived) AS cards
        UNWIND cards AS m
        WITH DISTINCT m
        WHERE m IS NOT NULL
          AND ($focus = '' OR toLower(m.content) CONTAINS $focus
               OR toLower(m.metric_key) CONTAINS $focus)
        RETURN
            m.card_id AS evidence_id,
            m.metric_key AS metric_key,
            m.content AS observation,
            m.rationale AS rationale,
            m.tags AS tags,
            m.created_at AS date,
            $learner_id AS learner_id,
            'memory_card' AS source_type
        ORDER BY m.created_at DESC
        LIMIT 100
        """,
        learner_id=learner_id,
        focus=normalized_focus,
    )
    evidence = [_card_row_to_evidence(row) for row in rows]
    if not evidence:
        return ToolResult(
            "insufficient_evidence", [], "No investigation evidence was found."
        )
    return ToolResult("ok", evidence, "")


def suggest_next_steps(learner_id: str) -> ToolResult:
    """Suggest evidence-gathering actions from observed coverage gaps."""
    result = get_strengths_and_gaps(learner_id)
    if result.status == "error":
        return result
    if result.status != "ok":
        return ToolResult(
            "insufficient_evidence",
            [],
            "More learner evidence is needed before suggesting next steps.",
        )

    gaps = result.data.get("gaps", []) if isinstance(result.data, dict) else []
    steps = [
        {
            "area": gap["area"],
            "action": (
                "Collect a learner submission or mentor observation that directly "
                f"covers {gap['area']}."
            ),
            "reason": gap["reason"],
        }
        for gap in gaps
    ]
    if not steps:
        steps = [
            {
                "area": "evidence depth",
                "action": (
                    "Collect a recent, directly attributable outcome or mentor "
                    "review."
                ),
                "reason": "Existing observations do not establish broader capability.",
            }
        ]
    return ToolResult("ok", steps, "")
