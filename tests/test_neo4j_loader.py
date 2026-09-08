"""
Integration tests for the graph database layer: connection, schema
initialization, and the batch loader - exercised against a real Neo4j
instance, not mocked.

Run with a live database:

    docker compose up -d neo4j
    docker compose run --rm api pytest tests/test_neo4j_loader.py

The whole module is skipped (not failed) when Neo4j isn't reachable, so
the existing CI job - which runs pytest with ``--no-deps`` and therefore
never starts Neo4j - is unaffected.

Safety: every test uses ids stamped with a per-run random prefix
(``_RUN``) and only ever deletes rows carrying that prefix. Nothing here
ever runs an unscoped ``MATCH (n) DETACH DELETE n`` against the target
database - a blanket wipe was flagged as unsafe in review on a related
script (scripts/verify_neo4j.py) and the same principle applies here.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import datetime, timezone

import pytest
from neo4j import Driver
from neo4j.exceptions import ServiceUnavailable

from src.app.graph import connections
from src.app.graph.constraints import initialize_schema
from src.app.graph.ids import node_id
from src.app.graph.schema import (
    DataSource,
    DataSourceName,
    Edge,
    EdgeType,
    LearnerGraph,
    LearnerProfile,
    LearnerRole,
    MemoryCard,
    ReviewPayload,
)
from src.app.ingestion.loader import load_graph

NOW = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
_RUN = uuid.uuid4().hex[:8]


def _key(name: str) -> str:
    """A natural key stamped with this test run's prefix, so cleanup can
    scope to exactly what this run created."""
    return f"test-{_RUN}-{name}"


def _cleanup(driver: Driver) -> None:
    prefix = f"test-{_RUN}-"
    with driver.session() as session:
        session.run(
            "MATCH (n) WHERE "
            "n.learner_id STARTS WITH $prefix OR "
            "n.datasource_id STARTS WITH $prefix OR "
            "n.card_id STARTS WITH $prefix "
            "DETACH DELETE n",
            prefix=prefix,
        )


@pytest.fixture(scope="module")
def driver() -> Iterator[Driver]:
    d = connections.get_driver()
    try:
        d.verify_connectivity()
    except ServiceUnavailable:
        pytest.skip(
            "Neo4j is not reachable - run `docker compose up -d neo4j` first",
            allow_module_level=True,
        )
    yield d
    _cleanup(d)
    connections.close_driver()


@pytest.fixture(autouse=True)
def _clean_before_each_test(driver: Driver) -> None:
    _cleanup(driver)


def _learner(suffix: str, **overrides: object) -> LearnerProfile:
    base = dict(
        id=node_id("LearnerProfile", _key(f"learner-{suffix}")),
        created_at=NOW,
        learner_id=_key(f"learner-{suffix}"),
        name=f"Test Learner {suffix}",
        role=LearnerRole.MEMBER,
        group_name="test-group",
        round_name="test-round",
        added_at=NOW,
    )
    base.update(overrides)
    return LearnerProfile(**base)  # type: ignore[arg-type]


def _review_datasource(suffix: str) -> DataSource:
    datasource_id = _key(f"datasource-{suffix}")
    return DataSource(
        id=node_id("DataSource", datasource_id),
        created_at=NOW,
        datasource_id=datasource_id,
        datasource_name=DataSourceName.REVIEW,
        timestamp=NOW,
        payload=ReviewPayload(
            lx_id="lx-1",
            task_headline="Integration test task",
            attempt_number=1,
            hours_before_deadline=5.0,
            submission_text="Real submission text for the loader test.",
            verdict="passed",
            feedback_summary="Looks good.",
            mentor_reply="Nice work.",
        ),
    )


def _memory_card(suffix: str) -> MemoryCard:
    card_id = _key(f"card-{suffix}")
    return MemoryCard(
        id=node_id("MemoryCard", card_id),
        created_at=NOW,
        card_id=card_id,
        metric_key="digital_ai_skills.testing",
        content="Learner wrote integration tests against a real database.",
        rationale="Directly observed in the submission.",
        tags=["testing", "neo4j"],
    )


# ===========================================================================
# Test 1 - connection
# ===========================================================================


def test_connection(driver: Driver) -> None:
    driver.verify_connectivity()


# ===========================================================================
# Test 2 - schema initialization, twice
# ===========================================================================


def test_schema_initialization_is_idempotent(driver: Driver) -> None:
    initialize_schema(driver)
    with driver.session() as session:
        first = session.run(
            "SHOW CONSTRAINTS YIELD name RETURN count(*) AS c"
        ).single()["c"]

    initialize_schema(driver)  # must not raise on the second call
    with driver.session() as session:
        second = session.run(
            "SHOW CONSTRAINTS YIELD name RETURN count(*) AS c"
        ).single()["c"]

    assert first > 0
    assert first == second


# ===========================================================================
# Test 3 - entity ingestion
# ===========================================================================


def test_entity_ingestion(driver: Driver) -> None:
    learner = _learner("entity")
    graph = LearnerGraph(generated_at=NOW, nodes=[learner])

    load_graph(driver, graph)

    with driver.session() as session:
        record = session.run(
            "MATCH (l:LearnerProfile {id: $id}) RETURN l.name AS name",
            id=learner.id,
        ).single()
    assert record is not None
    assert record["name"] == learner.name


# ===========================================================================
# Test 4 - relation ingestion
# ===========================================================================


def test_relation_ingestion(driver: Driver) -> None:
    learner = _learner("relation")
    datasource = _review_datasource("relation")
    graph = LearnerGraph(
        generated_at=NOW,
        nodes=[learner, datasource],
        edges=[
            Edge(
                type=EdgeType.PRODUCED,
                source_label="LearnerProfile",
                source_id=learner.id,
                target_label="DataSource",
                target_id=datasource.id,
            )
        ],
    )

    load_graph(driver, graph)

    with driver.session() as session:
        record = session.run(
            "MATCH (l:LearnerProfile {id: $lid})"
            "-[:PRODUCED]->(d:DataSource {id: $did}) "
            "RETURN count(*) AS c",
            lid=learner.id,
            did=datasource.id,
        ).single()
    assert record["c"] == 1


# ===========================================================================
# Test 5 - evidence (DataSource.payload / MemoryCard) ingestion
# ===========================================================================


def test_evidence_ingestion(driver: Driver) -> None:
    """ "Evidence" in this schema is a DataSource's embedded payload (the
    submission/feedback record) plus the MemoryCard(s) distilled from it -
    there is no separate Evidence node in this project's model."""
    learner = _learner("evidence")
    datasource = _review_datasource("evidence")
    card = _memory_card("evidence")
    graph = LearnerGraph(
        generated_at=NOW,
        nodes=[learner, datasource, card],
        edges=[
            Edge(
                type=EdgeType.PRODUCED,
                source_label="LearnerProfile",
                source_id=learner.id,
                target_label="DataSource",
                target_id=datasource.id,
            ),
            Edge(
                type=EdgeType.EXTRACTED_INTO,
                source_label="DataSource",
                source_id=datasource.id,
                target_label="MemoryCard",
                target_id=card.id,
            ),
        ],
    )

    load_graph(driver, graph)

    with driver.session() as session:
        ds_record = session.run(
            "MATCH (d:DataSource {id: $id}) RETURN d.payload_json AS payload_json",
            id=datasource.id,
        ).single()
        card_record = session.run(
            "MATCH (m:MemoryCard {id: $id}) "
            "RETURN m.content AS content, m.tags AS tags",
            id=card.id,
        ).single()

    assert ds_record is not None
    assert '"verdict":"passed"' in ds_record["payload_json"].replace(" ", "")
    assert card_record is not None
    assert card_record["content"] == card.content
    assert list(card_record["tags"]) == card.tags


# ===========================================================================
# Test 6 - idempotency
# ===========================================================================


def test_idempotent_reload_does_not_duplicate(driver: Driver) -> None:
    learner = _learner("idempotent")
    datasource = _review_datasource("idempotent")
    card = _memory_card("idempotent")
    graph = LearnerGraph(
        generated_at=NOW,
        nodes=[learner, datasource, card],
        edges=[
            Edge(
                type=EdgeType.PRODUCED,
                source_label="LearnerProfile",
                source_id=learner.id,
                target_label="DataSource",
                target_id=datasource.id,
            ),
            Edge(
                type=EdgeType.HAS_MEMORY_CARD,
                source_label="LearnerProfile",
                source_id=learner.id,
                target_label="MemoryCard",
                target_id=card.id,
            ),
        ],
    )

    load_graph(driver, graph)
    load_graph(driver, graph)  # same batch, again

    with driver.session() as session:
        node_count = session.run(
            "MATCH (n) WHERE n.id IN $ids RETURN count(n) AS c",
            ids=[learner.id, datasource.id, card.id],
        ).single()["c"]
        edge_count = session.run(
            "MATCH (l:LearnerProfile {id: $lid})-[r]->() RETURN count(r) AS c",
            lid=learner.id,
        ).single()["c"]

    assert node_count == 3  # not 6
    assert edge_count == 2  # PRODUCED + HAS_MEMORY_CARD, not 4


# ===========================================================================
# Test 7 - transaction failure leaves nothing committed
# ===========================================================================


def test_transaction_rolls_back_on_failure(driver: Driver) -> None:
    learner = _learner("txn")

    def _write_then_fail(tx: object) -> None:
        from src.app.graph import queries
        from src.app.graph.serialization import flatten_node

        queries.merge_nodes(tx, "LearnerProfile", [flatten_node(learner)])  # type: ignore[arg-type]
        raise RuntimeError("simulated mid-batch failure")

    with driver.session() as session:
        with pytest.raises(RuntimeError, match="simulated mid-batch failure"):
            session.execute_write(_write_then_fail)

    with driver.session() as session:
        record = session.run(
            "MATCH (l:LearnerProfile {id: $id}) RETURN count(l) AS c",
            id=learner.id,
        ).single()
    assert record["c"] == 0, "the write before the failure must not be committed"
