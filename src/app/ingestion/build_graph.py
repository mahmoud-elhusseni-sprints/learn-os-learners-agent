"""
Adapter: preprocessing-pipeline output -> a validated ``LearnerGraph``.

The missing link in the pipeline. ``src/app/ingestion/pipeline.py`` writes
three JSON files (learner profiles, DataSource nodes, memory cards) built
from the models in ``src/app/models/deliverables.py``. The batch loader in
``src/app/ingestion/loader.py`` takes a ``LearnerGraph`` built from the
models in ``src/app/graph/schema.py``. Nothing joined the two, so extraction
output never reached Neo4j.

This module is that join. It reads the pipeline's dicts and returns a
``LearnerGraph`` ready for ``load_graph()``.

Memory cards specifically can arrive in two shapes, both real: Atia's
pipeline emits them flat (``content``/``rationale``/``tags`` on the row);
Elgazzar's separate meeting/chat card generator
(``src/app/ingestion/generate_memory_cards.py``, ``--format json`` or
``jsonl``) emits the raw-export shape instead, with those fields nested
inside ``normalized_payload``. Both are accepted - see
``_normalize_memory_card_row``. Elgazzar's script is not part of the
pipeline yet, so its output is passed in as an extra list rather than read
from the standard three files; see ``build_graph_from_files``.

Why an adapter instead of changing either side
-----------------------------------------------
The two model sets describe the same three entities with the same field
names - both were written against the mentor's spec - but they differ in
strictness. The pipeline's models are permissive (timestamps as strings,
most fields optional, no node ids) because extraction has to cope with
messy source data. The graph models are strict (UTC datetimes, enums,
bounded numbers, deterministic ids) because the database is the place
where bad data does lasting damage. Both are reasonable for their own job,
so rather than loosen the graph models or tighten the pipeline's, this
module converts between them in one auditable place.

Tolerant on input, strict on output
------------------------------------
Extraction output is real-world data and some of it will be incomplete. A
record this module cannot convert is **skipped and counted**, never
silently dropped and never allowed through half-formed: the returned graph
is always fully valid. Call ``build_graph_from_pipeline_output`` and check
``.skipped`` to see what did not make it.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from src.app.graph.ids import node_id
from src.app.graph.schema import (
    AssessmentAnswerItem,
    AssessmentPayload,
    DataSource,
    DataSourceName,
    Edge,
    EdgeType,
    LearnerGraph,
    LearnerProfile,
    LearnerRole,
    MemoryCard,
    ReviewPayload,
    RubricPointEvaluation,
    RubricPointStatus,
    StubPayload,
)

logger = logging.getLogger(__name__)

__all__ = ["BuildResult", "build_graph_from_pipeline_output", "build_graph_from_files"]


@dataclass
class BuildResult:
    """The graph, plus an honest account of what did not make it in.

    ``skipped`` is data that could not be converted - a real quality
    problem worth investigating upstream. ``duplicates`` is data that
    converted fine but repeated an id already seen in this batch - expected
    dedup, not a problem, but silently dropping the second copy without a
    record of it would violate the same "never silently drop" principle
    this module exists to uphold.
    """

    graph: LearnerGraph
    skipped: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)

    def summary(self) -> str:
        counts = ", ".join(f"{k}={v}" for k, v in self.graph.counts().items())
        return (
            f"{len(self.graph.nodes)} nodes ({counts}), "
            f"{len(self.graph.edges)} edges, {len(self.skipped)} skipped, "
            f"{len(self.duplicates)} duplicates collapsed"
        )


def _parse_utc(value: Any, fallback: datetime) -> datetime:
    """Pipeline timestamps are strings (or missing). The graph models need
    timezone-aware datetimes, so parse here and treat a bare timestamp as
    UTC rather than rejecting the record over a missing suffix."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return fallback
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return fallback
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _rubric_points(raw: Iterable[dict[str, Any]]) -> list[RubricPointEvaluation]:
    """Convert rubric points, dropping any that cannot be made valid.

    The pipeline allows every field to be null; the graph model does not.
    Nulls become empty strings / zeros rather than failing the whole review,
    but a genuinely unusable point (bad status, out-of-range confidence) is
    dropped so it cannot corrupt the record it belongs to.
    """
    points: list[RubricPointEvaluation] = []
    for item in raw or []:
        try:
            points.append(
                RubricPointEvaluation(
                    rubric_id=int(item.get("rubric_id") or 0),
                    category=item.get("category") or "unknown",
                    requirement=item.get("requirement") or "",
                    status=RubricPointStatus(item.get("status")),
                    evaluation_criteria=item.get("evaluation_criteria") or "",
                    reason=item.get("reason") or "",
                    confidence_score=float(item.get("confidence_score") or 0.0),
                )
            )
        except (ValueError, TypeError) as exc:
            logger.warning("skipping rubric point %r: %s", item.get("rubric_id"), exc)
    return points


def _review_payload(raw: dict[str, Any]) -> ReviewPayload:
    return ReviewPayload(
        lx_id=raw.get("lx_id") or "",
        task_headline=raw.get("task_headline") or "",
        attempt_number=max(1, int(raw.get("attempt_number") or 1)),
        hours_before_deadline=raw.get("hours_before_deadline"),
        submission_text=raw.get("submission_text") or "",
        assets=list(raw.get("assets") or []),
        verdict=raw.get("verdict") or "",
        feedback_summary=raw.get("feedback_summary") or "",
        mentor_reply=raw.get("mentor_reply") or "",
        detailed_rubric_evaluations=_rubric_points(
            raw.get("detailed_rubric_evaluations") or []
        ),
    )


def _normalize_memory_card_row(row: dict[str, Any]) -> dict[str, Any]:
    """Memory cards reach us in two different shapes, both real:

    - Atia's pipeline (``memory_card_extraction.py``) emits the flat shape:
      ``content``/``rationale``/``tags`` sit directly on the row.
    - Elgazzar's meeting/chat card generator (``generate_memory_cards.py``,
      ``--format json``/``jsonl``) emits the *raw export* shape instead - the
      same one ``meeting_memory_cards.jsonl`` itself uses - where those
      fields are nested one level down inside ``normalized_payload``, and
      the learner is a single ``learner_id`` rather than a list.

    Detect the nested shape and flatten it here, once, so the rest of this
    module only has to handle one row format.
    """
    if "normalized_payload" not in row:
        return row  # already flat (Atia's shape)

    payload = row.get("normalized_payload") or {}
    flat = dict(row)
    flat.setdefault("content", payload.get("content"))
    flat.setdefault("rationale", payload.get("rationale"))
    flat.setdefault("tags", payload.get("profile_hints") or payload.get("tags"))
    learner_id = row.get("learner_id")
    if learner_id and "associated_learner_ids" not in flat:
        flat["associated_learner_ids"] = [learner_id]
    return flat


def _assessment_payload(raw: dict[str, Any]) -> AssessmentPayload:
    score = float(raw.get("score") or 0.0)
    max_score = float(raw.get("max_score") or 0.0)
    # The graph model refuses score > max_score. Extraction can produce that
    # pair from incomplete source data, so widen max_score rather than throw
    # the whole assessment away - and say so.
    if score > max_score:
        logger.warning(
            "assessment %r has score %s > max_score %s; widening max_score",
            raw.get("lx_id"),
            score,
            max_score,
        )
        max_score = score

    answers: list[AssessmentAnswerItem] = []
    for item in raw.get("answers") or []:
        try:
            answers.append(
                AssessmentAnswerItem(
                    question_id=item.get("question_id") or "",
                    domain=item.get("domain") or "",
                    metric_key=item.get("metric_key") or "",
                    learner_answer=item.get("learner_answer") or "",
                    score=max(0.0, float(item.get("score") or 0.0)),
                    evaluation_notes=item.get("evaluation_notes") or "",
                )
            )
        except (ValueError, TypeError) as exc:
            logger.warning("skipping answer %r: %s", item.get("question_id"), exc)

    return AssessmentPayload(
        lx_id=raw.get("lx_id") or "",
        assessment_type=raw.get("assessment_type") or "",
        topic_id=raw.get("topic_id") or "",
        score=score,
        max_score=max_score,
        answers=answers,
    )


def build_graph_from_pipeline_output(
    profiles: list[dict[str, Any]],
    datasources: list[dict[str, Any]],
    memory_cards: list[dict[str, Any]],
    *,
    ingested_at: datetime | None = None,
) -> BuildResult:
    """Convert one pipeline run's output into a validated ``LearnerGraph``.

    ``profiles``     - rows from ``extract_learner_profiles``
    ``datasources``  - ``DataSource.model_dump()`` rows from the pipeline
    ``memory_cards`` - card rows from EITHER source: Atia's pipeline (flat
                       shape) or Elgazzar's meeting/chat generator (nested
                       ``normalized_payload`` shape) - pass one list, both,
                       or their concatenation; each row is normalized on
                       its own, so mixing sources in one call is fine

    Returns a ``BuildResult`` holding the graph and the list of skipped
    records. Raises only if the *converted* data is itself inconsistent -
    which would be a bug in this module, not in the input.
    """
    now = ingested_at or datetime.now(timezone.utc)
    skipped: list[str] = []
    duplicates: list[str] = []

    # ---- LearnerProfile -----------------------------------------------
    learner_nodes: dict[str, LearnerProfile] = {}  # learner_id -> node
    for row in profiles:
        learner_id = row.get("learner_id")
        if not learner_id:
            skipped.append("profile with no learner_id")
            continue
        if learner_id in learner_nodes:
            duplicates.append(f"profile {learner_id}: repeated in this batch")
            continue  # the pipeline can emit a learner once per group file
        try:
            learner_nodes[learner_id] = LearnerProfile(
                id=node_id("LearnerProfile", learner_id),
                created_at=now,
                learner_id=learner_id,
                name=row.get("name") or learner_id,
                role=LearnerRole(row.get("role") or "member"),
                group_name=row.get("group_name") or "",
                round_name=row.get("round_name") or "",
                added_at=_parse_utc(row.get("added_at"), now),
                learner_status=row.get("learner_status"),
            )
        except (ValueError, TypeError) as exc:
            skipped.append(f"profile {learner_id}: {exc}")

    # ---- DataSource ----------------------------------------------------
    datasource_nodes: dict[str, DataSource] = {}  # datasource_id -> node
    datasource_owner: dict[str, str] = {}  # datasource_id -> learner_id
    meeting_index: dict[tuple[str, str], str] = {}  # (learner, meeting) -> ds_id

    for row in datasources:
        datasource_id = row.get("datasource_id")
        if not datasource_id:
            skipped.append("datasource with no datasource_id")
            continue
        if datasource_id in datasource_nodes:
            duplicates.append(f"datasource {datasource_id}: repeated in this batch")
            continue

        raw_name = row.get("datasource_name")
        name_value = getattr(raw_name, "value", raw_name)
        try:
            datasource_name = DataSourceName(name_value)
        except ValueError:
            skipped.append(f"datasource {datasource_id}: unknown name {name_value!r}")
            continue

        raw_payload = row.get("payload") or {}
        try:
            if datasource_name is DataSourceName.REVIEW:
                payload: ReviewPayload | AssessmentPayload | StubPayload = (
                    _review_payload(raw_payload)
                )
            elif datasource_name is DataSourceName.ASSESSMENTS:
                payload = _assessment_payload(raw_payload)
            else:
                payload = StubPayload()

            datasource_nodes[datasource_id] = DataSource(
                id=node_id("DataSource", datasource_id),
                created_at=now,
                datasource_id=datasource_id,
                datasource_name=datasource_name,
                timestamp=_parse_utc(row.get("timestamp"), now),
                payload=payload,
            )
        except (ValueError, TypeError) as exc:
            skipped.append(f"datasource {datasource_id}: {exc}")
            continue

        owner = row.get("learner_id")
        if owner in learner_nodes:
            datasource_owner[datasource_id] = owner
            meeting_id = row.get("meeting_id")
            if datasource_name is DataSourceName.MEETINGS and meeting_id:
                meeting_index[(owner, str(meeting_id))] = datasource_id
        elif owner:
            skipped.append(
                f"datasource {datasource_id}: learner {owner} not in this batch, "
                f"PRODUCED edge omitted"
            )

    # ---- MemoryCard ----------------------------------------------------
    card_nodes: dict[str, MemoryCard] = {}
    card_owners: dict[str, list[str]] = {}
    card_meeting: dict[str, str] = {}

    for raw_row in memory_cards:
        row = _normalize_memory_card_row(raw_row)
        card_id = row.get("card_id")
        if not card_id:
            skipped.append("memory card with no card_id")
            continue
        if card_id in card_nodes:
            duplicates.append(f"memory card {card_id}: repeated in this batch")
            continue
        try:
            tags = list(row.get("tags") or row.get("profile_hints") or [])
            card_nodes[card_id] = MemoryCard(
                id=node_id("MemoryCard", card_id),
                created_at=_parse_utc(row.get("created_at"), now),
                card_id=card_id,
                metric_key=row.get("metric_key") or "",
                content=row.get("content") or "",
                rationale=row.get("rationale"),
                tags=tags,
            )
        except (ValueError, TypeError) as exc:
            skipped.append(f"memory card {card_id}: {exc}")
            continue

        owners = [
            lid
            for lid in (row.get("associated_learner_ids") or [])
            if lid in learner_nodes
        ]
        card_owners[card_id] = owners
        if row.get("meeting_id"):
            card_meeting[card_id] = str(row["meeting_id"])

    # ---- Edges ---------------------------------------------------------
    edges: list[Edge] = []

    for datasource_id, learner_id in datasource_owner.items():
        edges.append(
            Edge(
                type=EdgeType.PRODUCED,
                source_label="LearnerProfile",
                source_id=learner_nodes[learner_id].id,
                target_label="DataSource",
                target_id=datasource_nodes[datasource_id].id,
            )
        )

    for card_id, owners in card_owners.items():
        for learner_id in owners:
            edges.append(
                Edge(
                    type=EdgeType.HAS_MEMORY_CARD,
                    source_label="LearnerProfile",
                    source_id=learner_nodes[learner_id].id,
                    target_label="MemoryCard",
                    target_id=card_nodes[card_id].id,
                )
            )

        # EXTRACTED_INTO only when we can actually name the source record.
        # EXTRACTED_INTO is 1:N - a card has at most one source - so take the
        # first owning learner's meeting record and stop.
        meeting_id = card_meeting.get(card_id)
        if not meeting_id:
            continue
        for learner_id in owners:
            source_ds = meeting_index.get((learner_id, meeting_id))
            if source_ds:
                edges.append(
                    Edge(
                        type=EdgeType.EXTRACTED_INTO,
                        source_label="DataSource",
                        source_id=datasource_nodes[source_ds].id,
                        target_label="MemoryCard",
                        target_id=card_nodes[card_id].id,
                    )
                )
                break

    graph = LearnerGraph(
        generated_at=now,
        description="Built from preprocessing pipeline output by build_graph.py",
        nodes=[
            *learner_nodes.values(),
            *datasource_nodes.values(),
            *card_nodes.values(),
        ],
        edges=edges,
    )
    return BuildResult(graph=graph, skipped=skipped, duplicates=duplicates)


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    """Read either a JSON array (``.json``) or one-object-per-line
    (``.jsonl``, what Elgazzar's ``--format jsonl`` writes)."""
    if not path.exists():
        logger.warning("%s does not exist - treating as empty", path)
        return []
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    data = json.loads(text)
    return data if isinstance(data, list) else []


def build_graph_from_files(
    profiles_file: Path,
    datasource_file: Path,
    memory_cards_file: Path,
    *,
    extra_memory_cards_file: Path | None = None,
    ingested_at: datetime | None = None,
) -> BuildResult:
    """Same as ``build_graph_from_pipeline_output``, reading JSON files.

    ``extra_memory_cards_file`` is optional and separate from the pipeline's
    own ``memory_cards_file``: it is not produced by ``pipeline.py`` at all,
    but by Elgazzar's standalone ``generate_memory_cards.py --format json``
    (or ``jsonl`` - both are read the same way here). Pass it whenever that
    script has been run; omit it and this behaves exactly as before.

    A missing file is treated as empty so a partial pipeline run still
    produces a loadable graph.
    """
    cards = _read_json_list(memory_cards_file)
    if extra_memory_cards_file is not None:
        cards = cards + _read_json_list(extra_memory_cards_file)

    return build_graph_from_pipeline_output(
        _read_json_list(profiles_file),
        _read_json_list(datasource_file),
        cards,
        ingested_at=ingested_at,
    )
