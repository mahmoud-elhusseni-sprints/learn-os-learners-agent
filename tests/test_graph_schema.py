"""
Test suite for the Professional Learner Graph ontology (v2, minimal:
LearnerProfile / DataSource / MemoryCard).

Rewritten from scratch alongside the schema redesign - every test in the
previous suite referenced removed classes (Evidence, Task, Assessment,
SkillAssertion, ...) and would not even import. Coverage here targets what
the new models actually claim:

  * deterministic ids (ids.py)
  * timestamp / extra-property discipline (unchanged from v1)
  * DataSource.payload discriminated union matches datasource_name
  * AssessmentPayload.score never exceeds max_score
  * RubricPointEvaluation.confidence_score is bounded 0..1
  * Edge legality against EDGE_SPECS
  * LearnerGraph structural invariants (unique ids, edges resolve, cardinality)
  * serialization (flatten_node's payload_json JSON-stringification, Cypher
    literal rendering, MERGE-only / idempotent export)
  * the generated DDL (generate_constraints.py) covers exactly the 3 labels
  * the real fixture (sample_learner_seed.json) validates and is internally
    consistent

Runs under pytest (``pytest tests/test_graph_schema.py``) or standalone
(``python3 tests/test_graph_schema.py``).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

import src.app.graph.schema as M
import src.app.graph.serialization as CE
from scripts import generate_constraints as GS
from src.app.graph.ids import SPRINTS_GRAPH_NAMESPACE, node_id

HERE = Path(__file__).parent
FIXTURE = HERE / "fixtures" / "sample_learner_seed.json"
NOW = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)


# ===========================================================================
# Fixtures / builders
# ===========================================================================


def _learner(**kw) -> M.LearnerProfile:
    base = dict(
        id=node_id("LearnerProfile", "l1"),
        created_at=NOW,
        learner_id="l1",
        name="Learner One",
        role=M.LearnerRole.MEMBER,
        group_name="G2",
        round_name="round2",
        added_at=NOW,
    )
    base.update(kw)
    return M.LearnerProfile(**base)


def _review_payload(**kw) -> M.ReviewPayload:
    base = dict(
        lx_id="lx1",
        task_headline="single_submission",
        attempt_number=1,
        hours_before_deadline=12.5,
        submission_text="Here is my work.",
        verdict="passed",
        feedback_summary="Solid.",
        mentor_reply="Nice job.",
    )
    base.update(kw)
    return M.ReviewPayload(**base)


def _review_datasource(**kw) -> M.DataSource:
    base = dict(
        id=node_id("DataSource", "d1"),
        created_at=NOW,
        datasource_id="d1",
        datasource_name=M.DataSourceName.REVIEW,
        timestamp=NOW,
        payload=_review_payload(),
    )
    base.update(kw)
    return M.DataSource(**base)


def _memory_card(**kw) -> M.MemoryCard:
    base = dict(
        id=node_id("MemoryCard", "c1"),
        created_at=NOW,
        card_id="c1",
        metric_key="learning_goals.learner_tasks",
        content="Learner said X.",
    )
    base.update(kw)
    return M.MemoryCard(**base)


def _edge(**kw) -> M.Edge:
    base = dict(
        type=M.EdgeType.PRODUCED,
        source_label="LearnerProfile",
        source_id=node_id("LearnerProfile", "l1"),
        target_label="DataSource",
        target_id=node_id("DataSource", "d1"),
    )
    base.update(kw)
    return M.Edge(**base)


# ===========================================================================
# 1. Identifiers
# ===========================================================================


def test_namespace_is_reproducible():
    assert SPRINTS_GRAPH_NAMESPACE == uuid.uuid5(uuid.NAMESPACE_DNS, "graph.sprints.ai")


def test_ids_are_deterministic_and_v5():
    a = node_id("LearnerProfile", "l1")
    b = node_id("LearnerProfile", "l1")
    assert a == b
    assert uuid.UUID(a).version == 5


def test_ids_differ_by_label_and_by_key():
    assert node_id("LearnerProfile", "x") != node_id("DataSource", "x")
    assert node_id("LearnerProfile", "x") != node_id("LearnerProfile", "y")


def test_ids_are_case_and_whitespace_insensitive():
    assert node_id("LearnerProfile", " X ") == node_id("learnerprofile", "x")


# ===========================================================================
# 2. Timestamp and extra-property discipline
# ===========================================================================


def test_naive_timestamp_rejected():
    with pytest.raises(ValidationError, match="timezone-aware"):
        _learner(created_at=datetime(2026, 8, 31))


def test_non_utc_offset_normalised_to_utc():
    from datetime import timedelta

    tz5 = timezone(timedelta(hours=5))
    learner = _learner(created_at=datetime(2026, 8, 31, 17, 0, tzinfo=tz5))
    assert learner.created_at.tzinfo == timezone.utc
    assert learner.created_at.hour == 12


def test_extra_properties_forbidden():
    with pytest.raises(ValidationError, match="extra"):
        M.LearnerProfile(
            id=node_id("LearnerProfile", "l1"),
            created_at=NOW,
            learner_id="l1",
            name="X",
            role=M.LearnerRole.MEMBER,
            group_name="G",
            round_name="R",
            added_at=NOW,
            not_a_real_field="oops",
        )


# ===========================================================================
# 3. DataSource.payload discriminated union
# ===========================================================================


def test_review_payload_on_review_datasource_is_valid():
    ds = _review_datasource()
    assert isinstance(ds.payload, M.ReviewPayload)


def test_assessment_payload_on_review_datasource_rejected():
    with pytest.raises(ValidationError, match="requires a ReviewPayload"):
        _review_datasource(
            payload=M.AssessmentPayload(
                lx_id="x", assessment_type="x", topic_id="x", score=1, max_score=1
            )
        )


def test_review_payload_on_assessment_datasource_rejected():
    with pytest.raises(ValidationError, match="requires a AssessmentPayload"):
        M.DataSource(
            id=node_id("DataSource", "d2"),
            created_at=NOW,
            datasource_id="d2",
            datasource_name=M.DataSourceName.ASSESSMENTS,
            timestamp=NOW,
            payload=_review_payload(),
        )


@pytest.mark.parametrize("name", [M.DataSourceName.CHAT, M.DataSourceName.MEETINGS])
def test_stub_payload_required_for_chat_and_meetings(name):
    ds = M.DataSource(
        id=node_id("DataSource", f"d-{name.value}"),
        created_at=NOW,
        datasource_id=f"d-{name.value}",
        datasource_name=name,
        timestamp=NOW,
        payload=M.StubPayload(),
    )
    assert isinstance(ds.payload, M.StubPayload)

    with pytest.raises(ValidationError, match="requires a StubPayload"):
        M.DataSource(
            id=node_id("DataSource", f"d-{name.value}-bad"),
            created_at=NOW,
            datasource_id=f"d-{name.value}-bad",
            datasource_name=name,
            timestamp=NOW,
            payload=_review_payload(),
        )


def test_datasource_name_assesments_is_the_intentional_misspelling():
    # MD file / source data both spell it "assesments" - not a typo to fix.
    assert M.DataSourceName.ASSESSMENTS.value == "assesments"


# ===========================================================================
# 4. AssessmentPayload / RubricPointEvaluation validation
# ===========================================================================


def test_assessment_score_within_max_is_valid():
    payload = M.AssessmentPayload(
        lx_id="x", assessment_type="x", topic_id="x", score=8, max_score=10
    )
    assert payload.score <= payload.max_score


def test_assessment_score_exceeding_max_rejected():
    with pytest.raises(ValidationError, match="exceeds max_score"):
        M.AssessmentPayload(
            lx_id="x", assessment_type="x", topic_id="x", score=11, max_score=10
        )


def test_assessment_answer_item_requires_nonnegative_score():
    with pytest.raises(ValidationError):
        M.AssessmentAnswerItem(
            question_id="q1",
            domain="d",
            metric_key="k",
            learner_answer="a",
            score=-1,
            evaluation_notes="n",
        )


def test_rubric_confidence_score_bounded():
    with pytest.raises(ValidationError, match="less than or equal to 1"):
        M.RubricPointEvaluation(
            rubric_id=1,
            category="c",
            requirement="r",
            status=M.RubricPointStatus.YES,
            evaluation_criteria="e",
            reason="x",
            confidence_score=1.4,
        )
    with pytest.raises(ValidationError, match="greater than or equal to 0"):
        M.RubricPointEvaluation(
            rubric_id=1,
            category="c",
            requirement="r",
            status=M.RubricPointStatus.YES,
            evaluation_criteria="e",
            reason="x",
            confidence_score=-0.1,
        )


def test_attempt_number_must_be_at_least_one():
    with pytest.raises(ValidationError):
        _review_payload(attempt_number=0)


# ===========================================================================
# 5. Edge legality
# ===========================================================================


def test_registered_edges_accepted():
    _edge()  # PRODUCED LearnerProfile -> DataSource
    _edge(
        type=M.EdgeType.EXTRACTED_INTO,
        source_label="DataSource",
        source_id=node_id("DataSource", "d1"),
        target_label="MemoryCard",
        target_id=node_id("MemoryCard", "c1"),
    )
    _edge(
        type=M.EdgeType.HAS_MEMORY_CARD,
        source_label="LearnerProfile",
        source_id=node_id("LearnerProfile", "l1"),
        target_label="MemoryCard",
        target_id=node_id("MemoryCard", "c1"),
    )


def test_reversed_edge_direction_rejected():
    with pytest.raises(ValidationError, match="illegal relationship"):
        _edge(
            source_label="DataSource",
            source_id=node_id("DataSource", "d1"),
            target_label="LearnerProfile",
            target_id=node_id("LearnerProfile", "l1"),
        )


def test_edge_type_with_wrong_endpoint_labels_rejected():
    with pytest.raises(ValidationError, match="illegal relationship"):
        _edge(
            type=M.EdgeType.EXTRACTED_INTO,
            source_label="LearnerProfile",
            target_label="MemoryCard",
        )


def test_exactly_three_edge_specs_and_three_edge_types():
    assert len(M.EDGE_SPECS) == 3
    assert {e.value for e in M.EdgeType} == {
        "PRODUCED",
        "EXTRACTED_INTO",
        "HAS_MEMORY_CARD",
    }


# ===========================================================================
# 6. LearnerGraph structural invariants
# ===========================================================================


def test_minimal_valid_graph():
    learner = _learner()
    ds = _review_datasource()
    graph = M.LearnerGraph(
        generated_at=NOW,
        nodes=[learner, ds],
        edges=[_edge(source_id=learner.id, target_id=ds.id)],
    )
    assert graph.counts() == {"DataSource": 1, "LearnerProfile": 1}


def test_duplicate_node_ids_rejected():
    learner = _learner()
    dup_card = M.MemoryCard(
        id=learner.id,  # deliberately colliding with the learner's id
        created_at=NOW,
        card_id="dup",
        metric_key="k",
        content="c",
    )
    with pytest.raises(ValidationError, match="duplicate node ids"):
        M.LearnerGraph(generated_at=NOW, nodes=[learner, dup_card])


def test_dangling_edge_rejected():
    learner = _learner()
    with pytest.raises(ValidationError, match="does not exist"):
        M.LearnerGraph(
            generated_at=NOW,
            nodes=[learner],
            edges=[
                _edge(source_id=learner.id, target_id=node_id("DataSource", "ghost"))
            ],
        )


def test_edge_with_mislabelled_endpoint_rejected():
    learner = _learner()
    card = _memory_card()
    with pytest.raises(
        ValidationError, match="is a MemoryCard but the edge says DataSource"
    ):
        M.LearnerGraph(
            generated_at=NOW,
            nodes=[learner, card],
            edges=[
                _edge(
                    source_id=learner.id, target_id=card.id, target_label="DataSource"
                )
            ],
        )


def test_cardinality_violation_rejected_for_one_to_many_target():
    # PRODUCED is 1:N (one learner, many DataSources) - a DataSource with
    # two PRODUCED edges pointing at it violates "target has <= 1 edge".
    l1 = _learner()
    l2 = _learner(id=node_id("LearnerProfile", "l2"), learner_id="l2")
    ds = _review_datasource()
    with pytest.raises(ValidationError, match="cardinality violations"):
        M.LearnerGraph(
            generated_at=NOW,
            nodes=[l1, l2, ds],
            edges=[
                _edge(source_id=l1.id, target_id=ds.id),
                _edge(source_id=l2.id, target_id=ds.id),
            ],
        )


def test_many_to_many_has_memory_card_allows_fan_in_and_out():
    l1 = _learner()
    l2 = _learner(id=node_id("LearnerProfile", "l2"), learner_id="l2")
    card = _memory_card()
    graph = M.LearnerGraph(
        generated_at=NOW,
        nodes=[l1, l2, card],
        edges=[
            _edge(
                type=M.EdgeType.HAS_MEMORY_CARD,
                source_id=l1.id,
                target_label="MemoryCard",
                target_id=card.id,
            ),
            _edge(
                type=M.EdgeType.HAS_MEMORY_CARD,
                source_id=l2.id,
                target_label="MemoryCard",
                target_id=card.id,
            ),
        ],
    )
    assert len(graph.edges) == 2


# ===========================================================================
# 7. Serialization
# ===========================================================================


def test_flatten_node_json_stringifies_nested_payload():
    ds = _review_datasource()
    flat = CE.flatten_node(ds)
    assert "payload" not in flat
    assert "payload_json" in flat
    round_tripped = json.loads(flat["payload_json"])
    assert round_tripped["verdict"] == "passed"


def test_flatten_node_drops_the_label_discriminator():
    flat = CE.flatten_node(_learner())
    assert "label" not in flat


def test_flatten_memory_card_keeps_tags_as_a_plain_list():
    card = _memory_card(tags=["a", "b"])
    flat = CE.flatten_node(card)
    assert flat["tags"] == ["a", "b"]
    assert "tags_json" not in flat


def test_cypher_literal_escapes_quotes_and_newlines():
    assert CE.cypher_literal("O'Brien\nline2") == "'O\\'Brien\\nline2'"


def test_cypher_literal_renders_uuid_timestamp_and_enum():
    from enum import Enum

    class E(str, Enum):
        X = "x"

    assert CE.cypher_literal(E.X) == "'x'"
    assert "datetime(" in CE.cypher_literal(NOW, "created_at")


def test_export_is_merge_only_and_deterministic():
    learner = _learner()
    ds = _review_datasource()
    graph = M.LearnerGraph(
        generated_at=NOW,
        nodes=[learner, ds],
        edges=[_edge(source_id=learner.id, target_id=ds.id)],
    )
    cql = CE.export_graph(graph)
    assert "CREATE (" not in cql
    assert cql.count("MERGE (n:") == 2
    assert cql.count("MERGE (a)-[") == 1
    assert CE.export_graph(graph) == cql  # byte-stable / re-runnable


# ===========================================================================
# 8. Generated DDL (scripts/generate_constraints.py)
# ===========================================================================


def test_ddl_spec_covers_exactly_the_three_labels():
    GS._check_coverage()  # raises SystemExit on mismatch
    assert (
        set(GS.DDL_SPEC)
        == set(M.NODE_CLASSES)
        == {
            "LearnerProfile",
            "DataSource",
            "MemoryCard",
        }
    )


def test_ddl_statements_are_all_if_not_exists():
    py = GS.build_python()
    ns: dict = {}
    exec(py, ns)
    for stmt in ns["ALL_STATEMENTS"]:
        assert "IF NOT EXISTS" in stmt


def test_ddl_has_a_uniqueness_constraint_per_label():
    py = GS.build_python()
    ns: dict = {}
    exec(py, ns)
    for label in M.NODE_CLASSES:
        assert any(
            f"FOR (n:{label})" in s and "IS UNIQUE" in s for s in ns["CONSTRAINTS"]
        )


def test_cql_deliverable_is_no_hand_edit_and_lists_all_labels():
    text = GS.build()
    assert "GENERATED FILE" in text
    for label in M.NODE_CLASSES:
        assert label in text


# ===========================================================================
# 9. The real fixture
# ===========================================================================


def _load_fixture() -> M.LearnerGraph:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return M.LearnerGraph.model_validate(raw)


def test_fixture_validates():
    graph = _load_fixture()
    assert graph.nodes
    assert graph.edges


def test_fixture_has_all_three_node_labels():
    graph = _load_fixture()
    counts = graph.counts()
    assert set(counts) == {"LearnerProfile", "DataSource", "MemoryCard"}
    assert all(v > 0 for v in counts.values())


def test_fixture_learners_match_natural_ids():
    graph = _load_fixture()
    for learner in graph.by_label("LearnerProfile"):
        assert learner.id == node_id("LearnerProfile", learner.learner_id)  # type: ignore[attr-defined]


def test_fixture_every_datasource_payload_matches_its_name():
    graph = _load_fixture()
    expected = {
        M.DataSourceName.REVIEW: M.ReviewPayload,
        M.DataSourceName.ASSESSMENTS: M.AssessmentPayload,
        M.DataSourceName.CHAT: M.StubPayload,
        M.DataSourceName.MEETINGS: M.StubPayload,
    }
    for ds in graph.by_label("DataSource"):
        assert isinstance(ds.payload, expected[ds.datasource_name])  # type: ignore[attr-defined]


def test_fixture_synthetic_assessments_are_marked_as_such():
    graph = _load_fixture()
    assessments = [
        d
        for d in graph.by_label("DataSource")
        if d.datasource_name is M.DataSourceName.ASSESSMENTS  # type: ignore[attr-defined]
    ]
    assert assessments
    for ds in assessments:
        assert "SYNTHETIC" in ds.payload.assessment_type  # type: ignore[union-attr]


def test_fixture_every_learner_produced_at_least_one_datasource():
    graph = _load_fixture()
    produced_sources = {e.source_id for e in graph.edges_of(M.EdgeType.PRODUCED)}
    for learner in graph.by_label("LearnerProfile"):
        assert learner.id in produced_sources


def test_fixture_extracted_into_edges_originate_only_from_meetings_datasources():
    graph = _load_fixture()
    idx = graph.index()
    for e in graph.edges_of(M.EdgeType.EXTRACTED_INTO):
        source = idx[e.source_id]
        assert source.datasource_name is M.DataSourceName.MEETINGS  # type: ignore[union-attr]


def test_fixture_has_memory_cards_reachable_both_ways():
    graph = _load_fixture()
    card = graph.by_label("MemoryCard")[0]
    via_extraction = graph.edges_of(M.EdgeType.EXTRACTED_INTO, target_id=card.id)
    via_direct = graph.edges_of(M.EdgeType.HAS_MEMORY_CARD, target_id=card.id)
    assert via_extraction
    assert via_direct


def test_fixture_round_trips_through_json():
    graph = _load_fixture()
    again = M.LearnerGraph.model_validate(
        json.loads(graph.model_dump_json(exclude_none=True))
    )
    assert len(again.nodes) == len(graph.nodes)
    assert len(again.edges) == len(graph.edges)


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
