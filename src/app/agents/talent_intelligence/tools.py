import json as _json
import re
from typing import Any

from src.app.core import BEHAVIOR_METRICS
from src.app.graph.connections import get_driver
from src.app.models.models import ToolResult


def _run(cypher: str, **params: Any) -> list[dict[str, Any]]:
    try:
        with get_driver().session() as session:
            result = session.run(cypher, **params)
            return [dict(record) for record in result]
    except Exception:
        return []


def _load_jsonl(name: str) -> tuple[dict[str, Any], ...]:
    return ()


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
    return rows[0] if rows else None


def _cards_for_learner(learner_id: str) -> list[dict[str, Any]]:
    return _run(
        """
        MATCH (l:LearnerProfile {learner_id: $learner_id})
            -[:HAS_MEMORY_CARD]->(m:MemoryCard)
        OPTIONAL MATCH (ds:DataSource)-[:EXTRACTED_INTO]->(m)
        RETURN
            m.card_id    AS evidence_id,
            m.metric_key AS metric_key,
            m.content    AS observation,
            m.rationale  AS rationale,
            m.tags       AS tags,
            m.created_at AS date,
            $learner_id  AS learner_id,
            coalesce(
                m.source_ref, m.meeting_id, m.lx_id, ds.datasource_id, null
            ) AS source_ref,
            coalesce(
                m.source_type, ds.datasource_name, 'meeting_transcript'
            ) AS source_type
        ORDER BY m.created_at DESC
        """,
        learner_id=learner_id,
    )


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


def get_skill_proofs(learner_id: str, skill: str) -> ToolResult:
    normalized = skill.strip().lower()
    rows = _run(
        """
        MATCH (l:LearnerProfile {learner_id: $learner_id})
            -[:HAS_MEMORY_CARD]->(m:MemoryCard)
        OPTIONAL MATCH (ds:DataSource)-[:EXTRACTED_INTO]->(m)
        WHERE (toLower(m.content) CONTAINS $skill
               OR toLower(m.metric_key) CONTAINS $skill)
          AND m.metric_key <> 'learning_goals.learner_tasks'
        RETURN
            m.card_id    AS evidence_id,
            m.metric_key AS metric_key,
            m.content    AS observation,
            m.rationale  AS rationale,
            m.tags       AS tags,
            m.created_at AS date,
            $learner_id  AS learner_id,
            coalesce(
                m.source_ref, m.meeting_id, m.lx_id, ds.datasource_id, null
            ) AS source_ref,
            coalesce(
                m.source_type, ds.datasource_name, 'meeting_transcript'
            ) AS source_type
        ORDER BY m.created_at DESC
        """,
        learner_id=learner_id,
        skill=normalized,
    )
    evidence = [_card_row_to_evidence(r) for r in rows]
    if not evidence:
        return ToolResult(
            "insufficient_evidence", [], "No matching skill evidence was found."
        )
    return ToolResult("ok", evidence, "")


def get_behavioral_context(learner_id: str) -> ToolResult:
    metrics = list(BEHAVIOR_METRICS)
    rows = _run(
        """
        MATCH (l:LearnerProfile {learner_id: $learner_id})
            -[:HAS_MEMORY_CARD]->(m:MemoryCard)
        OPTIONAL MATCH (ds:DataSource)-[:EXTRACTED_INTO]->(m)
        WHERE m.metric_key IN $metrics
        RETURN
            m.card_id    AS evidence_id,
            m.metric_key AS metric_key,
            m.content    AS observation,
            m.rationale  AS rationale,
            m.tags       AS tags,
            m.created_at AS date,
            $learner_id  AS learner_id,
            coalesce(
                m.source_ref, m.meeting_id, m.lx_id, ds.datasource_id, null
            ) AS source_ref,
            coalesce(
                m.source_type, ds.datasource_name, 'meeting_transcript'
            ) AS source_type
        ORDER BY m.created_at DESC
        """,
        learner_id=learner_id,
        metrics=metrics,
    )
    evidence = [_card_row_to_evidence(r) for r in rows]
    if not evidence:
        return ToolResult(
            "insufficient_evidence", [], "No behavioral observations were found."
        )
    return ToolResult("ok", evidence, "")


def get_strengths_and_gaps(learner_id: str) -> ToolResult:
    metrics = list(BEHAVIOR_METRICS)
    rows = _run(
        """
        MATCH (l:LearnerProfile {learner_id: $learner_id})
            -[:HAS_MEMORY_CARD]->(m:MemoryCard)
        WHERE m.metric_key IN $metrics
        RETURN
            m.card_id    AS evidence_id,
            m.metric_key AS metric_key,
            m.content    AS observation,
            m.created_at AS date,
            'memory_card' AS source_type
        """,
        learner_id=learner_id,
        metrics=metrics,
    )

    if not rows:
        jsonl_records = _load_jsonl("meeting_memory_cards.jsonl")
        for rec in jsonl_records:
            if rec.get("learner_id") == learner_id and rec.get("metric_key") in metrics:
                obs = (
                    rec.get("observation")
                    or rec.get("content")
                    or (
                        rec.get("normalized_payload", {}).get("content", "")
                        if isinstance(rec.get("normalized_payload"), dict)
                        else ""
                    )
                )
                rows.append(
                    {
                        "evidence_id": rec.get("card_id") or rec.get("evidence_id"),
                        "metric_key": rec.get("metric_key"),
                        "observation": obs,
                        "date": rec.get("date") or rec.get("created_at"),
                        "source_type": rec.get("source_type", "memory_card"),
                    }
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
    demonstrated = [
        r
        for r in rows
        if _POSITIVE.search(r.get("observation", ""))
        and not _NEGATIVE.search(r.get("observation", ""))
    ]
    strengths = [
        {
            "area": r["metric_key"],
            "evidence_ids": [r["evidence_id"]],
            "most_recent_date": str(r["date"]) if r.get("date") else None,
            "observation": r["observation"],
            "source_type": r["source_type"],
        }
        for r in demonstrated
    ]
    present = {r["metric_key"] for r in rows}
    gaps = [
        {
            "area": area,
            "status": "insufficient_evidence",
            "reason": "No matching observation was found in the graph.",
        }
        for area in sorted(BEHAVIOR_METRICS - present)
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
        payload: dict[str, Any] = {}
        if row.get("payload_json"):
            try:
                payload = _json.loads(row["payload_json"])
            except Exception:
                pass
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
