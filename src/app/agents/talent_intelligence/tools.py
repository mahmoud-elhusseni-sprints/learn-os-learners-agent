"""JSONL-backed mock investigation tools.

Only this module knows where the data comes from.  A Neo4j implementation can
replace these functions later while preserving their public interfaces.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .models import ToolResult

DATA_DIR = Path(__file__).resolve().parents[4] / "docs" / "data"
BEHAVIOR_METRICS = {
    "behavioral_engagement.engagement",
    "behavioral_engagement.effort_signals",
    "behavioral_engagement.adaptability",
}
OUTCOME_TAGS = {
    "learner_submission",
    "feedback_delivered",
    "grader_call",
    "attempt_passed",
    "task_closed",
    "lx_ended_success",
}


@lru_cache(maxsize=8)
def _load_jsonl(filename: str) -> tuple[dict[str, Any], ...]:
    """Load a JSONL file once per process; invalid rows are skipped safely."""
    path = DATA_DIR / filename
    if not path.exists():
        return ()
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as source:
        for line in source:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return tuple(rows)


def _find_learner(learner_query: str) -> dict[str, Any] | None:
    query = learner_query.strip().lower()
    if not query:
        return None
    for learner in _load_jsonl("learners.jsonl"):
        values = (
            learner.get("learner_id", ""),
            learner.get("name", ""),
            learner.get("email", ""),
        )
        if any(query == str(value).lower() for value in values):
            return learner
    return None


def _meeting_metadata() -> dict[str, dict[str, Any]]:
    return {
        str(row.get("meeting_id")): row
        for row in _load_jsonl("meetings.jsonl")
        if row.get("meeting_id")
    }


def _card_to_evidence(card: dict[str, Any]) -> dict[str, Any]:
    payload = card.get("normalized_payload") or {}
    metadata = payload.get("project_metadata") or {}
    meeting_id = card.get("meeting_id")
    meeting = _meeting_metadata().get(str(meeting_id), {}) if meeting_id else {}
    source_type = metadata.get("source_type", "meeting_memory_card")
    date = (
        metadata.get("scheduled_starts_at_utc")
        or payload.get("created_at")
        or card.get("created_at")
    )

    topic = (
        metadata.get("meeting_topic")
        or meeting.get("topic")
        or metadata.get("meeting_type")
        or "Meeting"
    )
    return {
        "evidence_id": card.get("card_id"),
        "learner_id": card.get("learner_id"),
        "source_type": source_type,
        "source_ref": metadata.get("source_id") or card.get("meeting_id"),
        "date": date,
        "observation": payload.get("content", ""),
        "context": topic,
        "tags": list(metadata.get("tags") or []),
        "metric_key": card.get("metric_key"),
        "rationale": payload.get("rationale", ""),
    }


def get_learner_profile(learner_query: str) -> ToolResult:
    """Return profile context only; no inferred capability claims."""
    learner = _find_learner(learner_query)
    if learner is None:
        return ToolResult("not_found", None, "Learner not found.")
    profile = {
        key: learner.get(key)
        for key in (
            "learner_id",
            "name",
            "email",
            "group_id",
            "group_name",
            "round_name",
            "learner_status",
        )
    }
    cards = [
        card
        for card in _load_jsonl("meeting_memory_cards.jsonl")
        if card.get("learner_id") == learner["learner_id"]
    ]
    profile["evidence_coverage"] = {
        "evidence_count": len(cards),
        "most_recent_evidence_date": max(
            ((_card_to_evidence(card).get("date") or "") for card in cards),
            default=None,
        ),
        "source_types": sorted(
            {_card_to_evidence(card)["source_type"] for card in cards}
        ),
    }
    return ToolResult("ok", profile)


def get_skill_proofs(learner_id: str, skill: str) -> ToolResult:
    """Return cards explicitly matching a requested skill, never task assignments alone."""  # noqa: E501
    normalized = skill.strip().lower()
    evidence: list[dict[str, Any]] = []
    for card in _load_jsonl("meeting_memory_cards.jsonl"):
        if card.get("learner_id") != learner_id:
            continue
        item = _card_to_evidence(card)
        searchable = " ".join(
            [item["observation"], item["metric_key"] or "", *item["tags"]]
        ).lower()
        if normalized not in searchable:
            continue
        # An assignment says what was requested, not what was demonstrated.
        if item["metric_key"] == "learning_goals.learner_tasks":
            continue
        evidence.append(item)
    evidence.sort(key=lambda item: item.get("date") or "", reverse=True)
    if not evidence:
        return ToolResult(
            "insufficient_evidence", [], "No matching skill evidence was found."
        )
    return ToolResult("ok", evidence)


def get_behavioral_context(learner_id: str) -> ToolResult:
    """Return contextual behavior observations; no personality inferences."""
    evidence: list[dict[str, Any]] = []
    for card in _load_jsonl("meeting_memory_cards.jsonl"):
        if card.get("learner_id") != learner_id:
            continue
        item = _card_to_evidence(card)
        if item["metric_key"] in BEHAVIOR_METRICS:
            evidence.append(item)
    evidence.sort(key=lambda item: item.get("date") or "", reverse=True)
    if not evidence:
        return ToolResult(
            "insufficient_evidence", [], "No behavioral observations were found."
        )
    return ToolResult("ok", evidence)


def get_strengths_and_gaps(learner_id: str) -> ToolResult:
    """Summarize observed evidence categories and state known coverage gaps."""
    cards = [
        card
        for card in _load_jsonl("meeting_memory_cards.jsonl")
        if card.get("learner_id") == learner_id
    ]
    if not cards:
        return ToolResult(
            "not_found",
            {"strengths": [], "gaps": []},
            "Learner has no evidence records.",
        )
    evidence = [_card_to_evidence(card) for card in cards]
    demonstrated = [
        item
        for item in evidence
        if item["metric_key"] != "learning_goals.learner_tasks"
    ]
    strengths = [
        {
            "area": item["metric_key"],
            "evidence_ids": [item["evidence_id"]],
            "most_recent_date": item["date"],
            "observation": item["observation"],
        }
        for item in demonstrated
    ]
    present = {item["metric_key"] for item in evidence}
    gaps = [
        {
            "area": area,
            "status": "insufficient_evidence",
            "reason": "No matching observation was found in the mock records.",
        }
        for area in sorted(BEHAVIOR_METRICS - present)
    ]
    return ToolResult("ok", {"strengths": strengths, "gaps": gaps})


def get_milestone_history(learner_id: str) -> ToolResult:
    """Return submission, feedback, and outcome events in chronological order."""
    milestones: list[dict[str, Any]] = []
    for row in _load_jsonl("interaction_logs.jsonl"):
        if row.get("learner_id") != learner_id:
            continue
        entry = row.get("entry") or {}
        tags = list(entry.get("tags") or [])
        summary = entry.get("summary", "")
        messages = entry.get("actor_messages") or []
        learner_message = next(
            (message for message in messages if message.get("from") == "learner"), None
        )
        learner_milestone = learner_message and any(
            phrase in (learner_message.get("text", "") + " " + summary).lower()
            for phrase in ("submitted", "completed", "finished", "passed", "score")
        )
        if not set(tags).intersection(OUTCOME_TAGS) and not learner_milestone:
            continue
        milestones.append(
            {
                "event_id": f"{row.get('lx_id')}:{row.get('entry_index')}",
                "date": entry.get("ts") or row.get("activated_at"),
                "summary": summary,
                "tags": tags,
                "source_type": "interaction_log",
                "context": (
                    "Learner-authored message"
                    if learner_message
                    else "LX workflow event"
                ),
            }
        )
    milestones.sort(key=lambda item: item.get("date") or "")
    if not milestones:
        return ToolResult(
            "insufficient_evidence", [], "No milestone history was found."
        )
    return ToolResult("ok", milestones)
