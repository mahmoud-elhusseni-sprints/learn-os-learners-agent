"""
Tests for the extraction -> graph adapter (``src/app/ingestion/build_graph.py``).

These are deliberately written as **contract tests**: the input fixtures are
not hand-typed dicts, they are produced by calling ``.model_dump()`` on the
pipeline's own models in ``src/app/models/deliverables.py``. If the pipeline
changes the shape of its output, these tests fail - which is the point. A
hand-written fixture would keep passing while the real integration quietly
broke.

Everything here runs without a database. The one test that needs Neo4j skips
itself when none is reachable, matching tests/test_batch_loader.py.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.app.graph.schema import DataSourceName, EdgeType, LearnerGraph
from src.app.ingestion.build_graph import build_graph_from_pipeline_output
from src.app.models.deliverables import (
    DataSource as PipelineDataSource,
)
from src.app.models.deliverables import (
    DataSourceType,
    ReviewPayload,
    RubricPointEvaluation,
)
from src.app.models.deliverables import (
    MemoryCard as PipelineMemoryCard,
)

NOW = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)

LEARNER_A = "127c834c-f7ce-4cc7-9a73-c8f93c8648aa"
LEARNER_B = "9a1e29a3-b6f8-43cc-b4a7-6fcfb72bd201"


def _profile(learner_id: str, name: str) -> dict:
    """Exactly the shape extract_learner_profiles() emits."""
    return {
        "learner_id": learner_id,
        "name": name,
        "role": "member",
        "group_name": "G2 - AI Engineer Internship",
        "round_name": "round2",
        "added_at": "2026-07-15T11:57:18.663341+00:00",
        "learner_status": None,
    }


def _review_datasource(learner_id: str, suffix: str) -> dict:
    """Built through the pipeline's own model, then dumped - so this fixture
    tracks their real output format."""
    return PipelineDataSource(
        datasource_id=f"review:{learner_id}:{suffix}",
        datasource_name=DataSourceType.REVIEW,
        timestamp="2026-07-30T10:17:08.550Z",
        learner_id=learner_id,
        payload=ReviewPayload(
            lx_id=f"lx-{suffix}",
            task_headline="Build the thing",
            attempt_number=1,
            hours_before_deadline=5.0,
            submission_text="here is my work",
            verdict="passed",
            feedback_summary="solid",
            mentor_reply="nice job",
            detailed_rubric_evaluations=[
                RubricPointEvaluation(
                    rubric_id=1,
                    category="digital_ai_skills",
                    requirement="ship it",
                    status="Yes",
                    evaluation_criteria="it runs",
                    reason="it ran",
                    confidence_score=0.95,
                )
            ],
        ),
    ).model_dump()


def _memory_card(card_id: str, learner_ids: list[str]) -> dict:
    return PipelineMemoryCard(
        card_id=card_id,
        metric_key="learning_goals.learner_tasks",
        content="The learner described their task.",
        rationale="Stated directly in the meeting.",
        tags=["task_assignment"],
        created_at="2026-07-27T20:30:11.396259+00:00",
        associated_learner_ids=learner_ids,
    ).model_dump()


# ===========================================================================
# The happy path
# ===========================================================================


def test_pipeline_output_becomes_a_valid_graph() -> None:
    result = build_graph_from_pipeline_output(
        profiles=[_profile(LEARNER_A, "Learner A1")],
        datasources=[_review_datasource(LEARNER_A, "1")],
        memory_cards=[_memory_card("card-1", [LEARNER_A])],
        ingested_at=NOW,
    )

    assert isinstance(result.graph, LearnerGraph)
    assert result.graph.counts() == {
        "DataSource": 1,
        "LearnerProfile": 1,
        "MemoryCard": 1,
    }
    assert result.skipped == []


def test_edges_are_built_from_the_pipeline_links() -> None:
    result = build_graph_from_pipeline_output(
        profiles=[_profile(LEARNER_A, "Learner A1")],
        datasources=[_review_datasource(LEARNER_A, "1")],
        memory_cards=[_memory_card("card-1", [LEARNER_A])],
        ingested_at=NOW,
    )

    produced = result.graph.edges_of(EdgeType.PRODUCED)
    has_card = result.graph.edges_of(EdgeType.HAS_MEMORY_CARD)
    assert len(produced) == 1, "DataSource.learner_id should become a PRODUCED edge"
    assert len(has_card) == 1, "associated_learner_ids should become HAS_MEMORY_CARD"


def test_review_payload_survives_the_conversion() -> None:
    result = build_graph_from_pipeline_output(
        profiles=[_profile(LEARNER_A, "Learner A1")],
        datasources=[_review_datasource(LEARNER_A, "1")],
        memory_cards=[],
        ingested_at=NOW,
    )
    ds = result.graph.by_label("DataSource")[0]
    assert ds.datasource_name is DataSourceName.REVIEW  # type: ignore[attr-defined]
    assert ds.payload.verdict == "passed"  # type: ignore[union-attr]
    assert len(ds.payload.detailed_rubric_evaluations) == 1  # type: ignore[union-attr]


def test_string_timestamps_become_utc_datetimes() -> None:
    result = build_graph_from_pipeline_output(
        profiles=[_profile(LEARNER_A, "Learner A1")],
        datasources=[],
        memory_cards=[],
        ingested_at=NOW,
    )
    learner = result.graph.by_label("LearnerProfile")[0]
    assert learner.added_at.tzinfo is not None  # type: ignore[attr-defined]
    assert learner.added_at.utcoffset().total_seconds() == 0  # type: ignore[attr-defined,union-attr]


def test_ids_are_deterministic_across_runs() -> None:
    """Two separate builds of the same input produce the same node ids -
    which is what lets the loader MERGE instead of duplicating."""
    args = dict(
        profiles=[_profile(LEARNER_A, "Learner A1")],
        datasources=[_review_datasource(LEARNER_A, "1")],
        memory_cards=[_memory_card("card-1", [LEARNER_A])],
        ingested_at=NOW,
    )
    first = build_graph_from_pipeline_output(**args)  # type: ignore[arg-type]
    second = build_graph_from_pipeline_output(**args)  # type: ignore[arg-type]
    assert sorted(n.id for n in first.graph.nodes) == sorted(
        n.id for n in second.graph.nodes
    )


# ===========================================================================
# Messy input - the adapter must stay standing
# ===========================================================================


def test_profile_without_learner_id_is_skipped_not_fatal() -> None:
    result = build_graph_from_pipeline_output(
        profiles=[_profile(LEARNER_A, "Learner A1"), {"name": "no id here"}],
        datasources=[],
        memory_cards=[],
        ingested_at=NOW,
    )
    assert len(result.graph.by_label("LearnerProfile")) == 1
    assert any("no learner_id" in s for s in result.skipped)


def test_datasource_for_unknown_learner_still_loads_without_the_edge() -> None:
    """A record whose learner isn't in this batch must not be dropped, and
    must not produce a dangling edge that fails whole-graph validation."""
    result = build_graph_from_pipeline_output(
        profiles=[_profile(LEARNER_A, "Learner A1")],
        datasources=[_review_datasource(LEARNER_B, "orphan")],
        memory_cards=[],
        ingested_at=NOW,
    )
    assert len(result.graph.by_label("DataSource")) == 1
    assert result.graph.edges_of(EdgeType.PRODUCED) == []
    assert any("not in this batch" in s for s in result.skipped)


def test_duplicate_records_are_collapsed() -> None:
    """The pipeline reads several group files and can emit a learner twice.
    Duplicate ids would fail LearnerGraph validation, so they're collapsed."""
    result = build_graph_from_pipeline_output(
        profiles=[_profile(LEARNER_A, "Learner A1"), _profile(LEARNER_A, "Learner A1")],
        datasources=[
            _review_datasource(LEARNER_A, "1"),
            _review_datasource(LEARNER_A, "1"),
        ],
        memory_cards=[],
        ingested_at=NOW,
    )
    assert len(result.graph.by_label("LearnerProfile")) == 1
    assert len(result.graph.by_label("DataSource")) == 1


def test_null_rubric_fields_do_not_kill_the_review() -> None:
    """The pipeline allows every rubric field to be null; the graph model
    does not. The review must survive with the point converted."""
    row = _review_datasource(LEARNER_A, "1")
    row["payload"]["detailed_rubric_evaluations"] = [
        {
            "rubric_id": None,
            "status": "Partial",
            "reason": None,
            "evaluation_criteria": None,
            "confidence_score": None,
            "category": "digital_ai_skills",
            "requirement": "",
        }
    ]
    result = build_graph_from_pipeline_output(
        profiles=[_profile(LEARNER_A, "Learner A1")],
        datasources=[row],
        memory_cards=[],
        ingested_at=NOW,
    )
    ds = result.graph.by_label("DataSource")[0]
    assert len(ds.payload.detailed_rubric_evaluations) == 1  # type: ignore[union-attr]


def test_unparseable_rubric_status_drops_only_that_point() -> None:
    row = _review_datasource(LEARNER_A, "1")
    row["payload"]["detailed_rubric_evaluations"] = [
        {"status": "definitely not a valid status", "category": "x", "requirement": ""}
    ]
    result = build_graph_from_pipeline_output(
        profiles=[_profile(LEARNER_A, "Learner A1")],
        datasources=[row],
        memory_cards=[],
        ingested_at=NOW,
    )
    ds = result.graph.by_label("DataSource")[0]
    assert ds.payload.detailed_rubric_evaluations == []  # type: ignore[union-attr]
    assert (
        ds.payload.verdict == "passed"
    )  # the record itself survived  # type: ignore[union-attr]


def test_empty_input_produces_an_empty_but_valid_graph() -> None:
    result = build_graph_from_pipeline_output([], [], [], ingested_at=NOW)
    assert result.graph.nodes == []
    assert result.graph.edges == []


# ===========================================================================
# The real end of the seam: does it actually load?
# ===========================================================================


def test_adapter_output_loads_into_neo4j() -> None:
    from neo4j.exceptions import ServiceUnavailable

    from src.app.graph import connections
    from src.loader.graph_loader import initialize_schema, load_graph

    driver = connections.get_driver()
    try:
        driver.verify_connectivity()
    except ServiceUnavailable:
        pytest.skip("Neo4j is not reachable - run `docker compose up -d neo4j` first")

    learner_id = "adapter-test-learner"
    result = build_graph_from_pipeline_output(
        profiles=[_profile(learner_id, "Adapter Test")],
        datasources=[_review_datasource(learner_id, "1")],
        memory_cards=[_memory_card("adapter-test-card", [learner_id])],
        ingested_at=NOW,
    )

    initialize_schema(driver)
    load_graph(driver, result.graph)
    load_graph(driver, result.graph)  # idempotent

    try:
        with driver.session() as session:
            count = session.run(
                "MATCH (l:LearnerProfile {learner_id: $lid})"
                "-[:PRODUCED]->(d:DataSource) "
                "RETURN count(d) AS c",
                lid=learner_id,
            ).single()["c"]
        assert count == 1, "two loads must not duplicate the DataSource"
    finally:
        with driver.session() as session:
            session.run(
                "MATCH (n) WHERE n.learner_id = $lid OR n.card_id = $cid "
                "OR n.datasource_id STARTS WITH $prefix DETACH DELETE n",
                lid=learner_id,
                cid="adapter-test-card",
                prefix=f"review:{learner_id}",
            )
