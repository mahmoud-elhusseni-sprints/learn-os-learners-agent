"""
Build ``sample_learner_seed.json`` from the real anonymized internship export
(v2, minimal schema: LearnerProfile / DataSource / MemoryCard).

Rewritten alongside the schema redesign. The whole point of building the
fixture from the real export instead of hand-writing one is unchanged: it
proves the 3-node ontology actually fits the data Task 3's ingestion
pipeline will receive, not just that the Pydantic models are internally
consistent.

What real data backs each node/payload
---------------------------------------
  LearnerProfile        - every row of learners.jsonl (7 learners, real).
  DataSource("review")  - one per CLOSED grading cycle found in
                           interaction_logs.jsonl (tags "grader_call" +
                           "feedback_delivered" with a non-null verdict).
                           submission_text/verdict/feedback_summary/
                           mentor_reply/rubric points are all real, taken
                           verbatim from the export.
  DataSource("assesments") - SYNTHETIC. The export contains no LMS-style
                           assessment records for this group (only
                           virtual-internship task submissions), so one
                           clearly-marked illustrative record per learner
                           is generated to prove the payload shape parses.
                           Flagged in the handoff report - do not mistake
                           these for real assessment data.
  DataSource("meetings")  - one per (learner, meeting) pair actually
                           referenced by that learner's memory cards, real
                           meeting_id/timestamp from meetings.jsonl. Empty
                           payload, per the MD file's own stub shape.
  MemoryCard             - every row of meeting_memory_cards.jsonl, real.

hours_before_deadline (ReviewPayload) - open semantics question
-----------------------------------------------------------------
The export has no structured deadline field; a deadline sometimes appears
as free text inside the task-kickoff brief ("Deadline: Thursday, July 30,
2026, at 11:59 PM Cairo time."). Where that text is present and parseable,
this hours-before-deadline is computed from it (Cairo = UTC+2, fixed
offset, close enough for a fixture). Where it is not present or not
parseable, the value is 0.0 and the record is marked in
``_DEADLINE_UNRESOLVED`` - this is the same open "hours_before_deadline
semantics" question raised earlier and NOT to be treated as resolved by
this script; it is a best-effort fixture value, not a confirmed answer.

Usage
-----
    python3 scripts/build_seed.py --logs-dir "/path/to/group-a-ai-engineer"
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import src.app.graph.schema as M
from src.app.graph.ids import node_id

INGESTED_AT = datetime(2026, 8, 31, 12, 0, 0, tzinfo=timezone.utc)
CAIRO_OFFSET = timezone(timedelta(hours=2))

_DEADLINE_UNRESOLVED: list[str] = []


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
# Best-effort deadline extraction from task-kickoff free text - see module
# docstring. Not a confirmed semantics answer, just a fixture heuristic.
# ===========================================================================

_DEADLINE_RE = re.compile(
    r"Deadline:\s*\n?-?\s*"
    r"(?:[A-Za-z]+,\s*)?"
    r"([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4}),\s*at\s*(\d{1,2}):(\d{2})\s*(AM|PM)\s*"
    r"Cairo time",
    re.IGNORECASE,
)


def parse_deadline_cairo(text: str) -> datetime | None:
    m = _DEADLINE_RE.search(text)
    if not m:
        return None
    month_name, day, year, hour, minute, ampm = m.groups()
    try:
        naive = datetime.strptime(
            f"{month_name} {day} {year} {hour}:{minute} {ampm.upper()}",
            "%B %d %Y %I:%M %p",
        )
    except ValueError:
        return None
    return naive.replace(tzinfo=CAIRO_OFFSET).astimezone(timezone.utc)


def kickoff_text_by_lx(logs: list[dict[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for d in logs:
        if "task_kickoff" not in d["entry"].get("tags", []):
            continue
        msgs = d["entry"].get("actor_messages", [])
        out[d["lx_id"]] = " ".join(m.get("text", "") for m in msgs)
    return out


# ===========================================================================
# LearnerProfile
# ===========================================================================


def build_learner_profiles(logs_dir: Path) -> list[M.LearnerProfile]:
    out: list[M.LearnerProfile] = []
    for row in jsonl(logs_dir / "learners.jsonl"):
        out.append(
            M.LearnerProfile(
                id=node_id("LearnerProfile", row["learner_id"]),
                created_at=INGESTED_AT,
                learner_id=row["learner_id"],
                name=row["name"],
                role=M.LearnerRole(row["role"]),
                group_name=row["group_name"],
                round_name=row["round_name"],
                added_at=ts(row["added_at"]) or INGESTED_AT,
                learner_status=row.get("learner_status"),
            )
        )
    return out


# ===========================================================================
# DataSource(review) - real grading cycles from interaction_logs.jsonl
# ===========================================================================


def _rubric_points(feedback_raw: str) -> list[M.RubricPointEvaluation]:
    """Best-effort extraction of the JSON rubric array embedded inside the
    free-text ``feedback.raw`` field. Several distinct rubric arrays can be
    concatenated back-to-back (scope + quality); each is parsed
    independently and any point that fails validation is dropped rather
    than aborting the whole record - a malformed one-off rubric point must
    not take down an otherwise-good real submission record."""
    points: list[M.RubricPointEvaluation] = []
    for m in re.finditer(
        r"\[\s*\{.*?\}\s*\](?=\s*(?:\n[A-Z][a-z]+ |\Z))", feedback_raw, re.S
    ):
        try:
            items = json.loads(m.group(0))
        except ValueError:
            continue
        if not isinstance(items, list):
            continue
        for item in items:
            for point in item.get("points", []):
                try:
                    points.append(
                        M.RubricPointEvaluation(
                            rubric_id=point["rubric_id"],
                            category=item.get("category", "unknown"),
                            requirement=item.get("requirement", ""),
                            status=M.RubricPointStatus(point["status"]),
                            evaluation_criteria=point.get("evaluation_criteria", ""),
                            reason=point.get("reason", ""),
                            confidence_score=point.get("confidence_score", 0.0),
                        )
                    )
                except (KeyError, ValueError):
                    continue
    return points


def build_review_datasources(
    logs_dir: Path, kickoff_text: dict[str, str]
) -> tuple[list[M.DataSource], dict[str, str]]:
    """Returns (datasources, {datasource.id: learner_id})."""
    logs = list(jsonl(logs_dir / "interaction_logs.jsonl"))
    closed = [
        d
        for d in logs
        if "grader_call" in d["entry"].get("tags", [])
        and d["entry"].get("feedback", {}).get("verdict")
    ]

    attempt_seen: dict[tuple[str, str], int] = {}
    out: list[M.DataSource] = []
    owners: dict[str, str] = {}

    for d in sorted(closed, key=lambda x: x["entry"]["ts"]):
        learner_id = d["learner_id"]
        lx_id = d["lx_id"]
        key = (learner_id, lx_id)
        attempt_seen[key] = attempt_seen.get(key, 0) + 1
        attempt_number = attempt_seen[key]

        entry = d["entry"]
        feedback = entry["feedback"]
        submission = entry.get("submission", {})
        submitted_at = ts(entry["ts"]) or INGESTED_AT

        deadline = parse_deadline_cairo(kickoff_text.get(lx_id, ""))
        if deadline is not None:
            hours_before_deadline = round(
                (deadline - submitted_at).total_seconds() / 3600, 2
            )
        else:
            hours_before_deadline = 0.0
            _DEADLINE_UNRESOLVED.append(f"{learner_id}/{lx_id}#{attempt_number}")

        assets = [
            a.get("url") or a.get("file_url")
            for a in submission.get("attachments", [])
            if a.get("url") or a.get("file_url")
        ]

        payload = M.ReviewPayload(
            lx_id=lx_id,
            task_headline=d.get("task_archetype_id", "task"),
            attempt_number=attempt_number,
            hours_before_deadline=hours_before_deadline,
            submission_text=submission.get("text", ""),
            assets=assets,
            verdict=feedback["verdict"],
            feedback_summary=feedback.get("summary", ""),
            mentor_reply=feedback.get("mentor_reply", ""),
            detailed_rubric_evaluations=_rubric_points(feedback.get("raw", "")),
        )

        datasource_id = f"review:{learner_id}:{lx_id}:{attempt_number}"
        node = M.DataSource(
            id=node_id("DataSource", datasource_id),
            created_at=INGESTED_AT,
            datasource_id=datasource_id,
            datasource_name=M.DataSourceName.REVIEW,
            timestamp=submitted_at,
            payload=payload,
        )
        out.append(node)
        owners[node.id] = learner_id

    return out, owners


# ===========================================================================
# DataSource(assesments) - SYNTHETIC, one illustrative record per learner.
# No real LMS assessment export exists for this group - see module docstring.
# ===========================================================================


def build_synthetic_assessment_datasources(
    learners: list[M.LearnerProfile],
) -> tuple[list[M.DataSource], dict[str, str]]:
    out: list[M.DataSource] = []
    owners: dict[str, str] = {}
    for learner in learners:
        payload = M.AssessmentPayload(
            lx_id="SYNTHETIC-assessment",
            assessment_type="SYNTHETIC-illustrative",
            topic_id="ai-engineering-fundamentals",
            score=0.0,
            max_score=0.0,
            answers=[],
        )
        datasource_id = f"assesments:{learner.learner_id}:synthetic"
        node = M.DataSource(
            id=node_id("DataSource", datasource_id),
            created_at=INGESTED_AT,
            datasource_id=datasource_id,
            datasource_name=M.DataSourceName.ASSESSMENTS,
            timestamp=INGESTED_AT,
            payload=payload,
        )
        out.append(node)
        owners[node.id] = learner.learner_id
    return out, owners


# ===========================================================================
# DataSource(meetings) - real (learner, meeting) pairs referenced by that
# learner's memory cards. Empty payload, per the MD file's stub shape.
# ===========================================================================


def build_meeting_datasources(
    logs_dir: Path, cards: list[dict[str, Any]]
) -> tuple[list[M.DataSource], dict[str, str], dict[tuple[str, str], str]]:
    meetings_by_id = {m["meeting_id"]: m for m in jsonl(logs_dir / "meetings.jsonl")}

    pairs: set[tuple[str, str]] = {(c["learner_id"], c["meeting_id"]) for c in cards}
    out: list[M.DataSource] = []
    owners: dict[str, str] = {}
    index: dict[tuple[str, str], str] = {}  # (learner_id, meeting_id) -> DataSource.id

    for learner_id, meeting_id in sorted(pairs):
        meeting = meetings_by_id.get(meeting_id, {})
        starts_at = ts(meeting.get("starts_at_utc")) or INGESTED_AT
        datasource_id = f"meetings:{learner_id}:{meeting_id}"
        node = M.DataSource(
            id=node_id("DataSource", datasource_id),
            created_at=INGESTED_AT,
            datasource_id=datasource_id,
            datasource_name=M.DataSourceName.MEETINGS,
            timestamp=starts_at,
            payload=M.StubPayload(),
        )
        out.append(node)
        owners[node.id] = learner_id
        index[(learner_id, meeting_id)] = node.id

    return out, owners, index


# ===========================================================================
# MemoryCard - every row of meeting_memory_cards.jsonl, real.
# ===========================================================================


def build_memory_cards(
    cards: list[dict[str, Any]],
) -> tuple[list[M.MemoryCard], dict[str, str], dict[str, str]]:
    """Returns (cards, {card.id: learner_id}, {card.id: meeting_id})."""
    out: list[M.MemoryCard] = []
    owners: dict[str, str] = {}
    from_meeting: dict[str, str] = {}

    for row in cards:
        payload = row.get("normalized_payload", {})
        node = M.MemoryCard(
            id=node_id("MemoryCard", row["card_id"]),
            created_at=ts(row.get("created_at")) or INGESTED_AT,
            card_id=row["card_id"],
            metric_key=row["metric_key"],
            content=payload.get("content", ""),
            rationale=payload.get("rationale"),
            tags=list(payload.get("profile_hints", [])),
        )
        out.append(node)
        owners[node.id] = row["learner_id"]
        from_meeting[node.id] = row["meeting_id"]

    return out, owners, from_meeting


# ===========================================================================
# Assemble
# ===========================================================================


def build_graph(logs_dir: Path) -> M.LearnerGraph:
    learners = build_learner_profiles(logs_dir)
    learner_by_natural_id = {learner.learner_id: learner for learner in learners}

    logs = list(jsonl(logs_dir / "interaction_logs.jsonl"))
    kickoff_text = kickoff_text_by_lx(logs)

    review_ds, review_owners = build_review_datasources(logs_dir, kickoff_text)
    assess_ds, assess_owners = build_synthetic_assessment_datasources(learners)

    cards_raw = list(jsonl(logs_dir / "meeting_memory_cards.jsonl"))
    meeting_ds, meeting_owners, meeting_index = build_meeting_datasources(
        logs_dir, cards_raw
    )
    memory_cards, card_owners, card_from_meeting = build_memory_cards(cards_raw)

    nodes: list[M.GraphNode] = [
        *learners,
        *review_ds,
        *assess_ds,
        *meeting_ds,
        *memory_cards,
    ]

    edges: list[M.Edge] = []

    def produced(datasource_id: str, owners: dict[str, str]) -> None:
        learner = learner_by_natural_id[owners[datasource_id]]
        edges.append(
            M.Edge(
                type=M.EdgeType.PRODUCED,
                source_label="LearnerProfile",
                source_id=learner.id,
                target_label="DataSource",
                target_id=datasource_id,
            )
        )

    for ds in review_ds:
        produced(ds.id, review_owners)
    for ds in assess_ds:
        produced(ds.id, assess_owners)
    for ds in meeting_ds:
        produced(ds.id, meeting_owners)

    for card in memory_cards:
        learner = learner_by_natural_id[card_owners[card.id]]
        meeting_id = card_from_meeting[card.id]
        source_ds_id = meeting_index[(learner.learner_id, meeting_id)]

        edges.append(
            M.Edge(
                type=M.EdgeType.EXTRACTED_INTO,
                source_label="DataSource",
                source_id=source_ds_id,
                target_label="MemoryCard",
                target_id=card.id,
            )
        )
        edges.append(
            M.Edge(
                type=M.EdgeType.HAS_MEMORY_CARD,
                source_label="LearnerProfile",
                source_id=learner.id,
                target_label="MemoryCard",
                target_id=card.id,
            )
        )

    return M.LearnerGraph(
        generated_at=INGESTED_AT,
        description=(
            "Sample fixture built from the real Group A (AI Engineer) "
            "internship export. All LearnerProfile, review DataSource and "
            "MemoryCard records are real; assesments DataSource records "
            "are SYNTHETIC/ILLUSTRATIVE (no real LMS assessment export "
            "exists for this group)."
        ),
        nodes=nodes,
        edges=edges,
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--logs-dir", required=True, type=Path)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent.parent
        / "tests"
        / "fixtures"
        / "sample_learner_seed.json",
    )
    args = ap.parse_args()

    graph = build_graph(args.logs_dir)
    args.out.write_text(
        graph.model_dump_json(indent=2, exclude_none=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {args.out} ({graph.counts()})")
    if _DEADLINE_UNRESOLVED:
        print(
            f"NOTE: hours_before_deadline defaulted to 0.0 for "
            f"{len(_DEADLINE_UNRESOLVED)} review record(s) - no parseable "
            f"deadline text found. This is the still-open "
            f"'hours_before_deadline semantics' question, not a bug."
        )
