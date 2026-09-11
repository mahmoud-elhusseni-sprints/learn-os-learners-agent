"""
Integration tests for the graph database layer: connection, schema
initialization, and the batch loader - exercised against a real Neo4j
instance, not mocked.

Run with a live database:

    docker compose up -d neo4j
    docker compose run --rm api pytest tests/test_batch_loader.py

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
from neo4j.exceptions import ClientError, ServiceUnavailable

from src.app.graph import connections
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

# Imported through the entry point the task brief names, which re-exports the
# implementation under src/app/. Testing through it keeps that contract honest.
from src.loader.graph_loader import (
    initialize_schema,
    load_graph,
    load_graph_atomic,
)

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


def test_invalid_payload_rolls_back_the_whole_batch(driver: Driver) -> None:
    """A payload the database itself rejects (not a hand-raised error): a
    property value Neo4j cannot store. The valid node written earlier in the
    same transaction must not survive."""
    good = _learner("rollback-good")
    bad_row = {
        "id": node_id("LearnerProfile", _key("rollback-bad")),
        "learner_id": _key("rollback-bad"),
        # Neo4j cannot store a nested map as a property value - this is
        # rejected by the server, mid-transaction, after the good row landed.
        "name": {"nested": "not a legal property value"},
    }

    def _write_good_then_invalid(tx: object) -> None:
        from src.app.graph import queries
        from src.app.graph.serialization import flatten_node

        queries.merge_nodes(tx, "LearnerProfile", [flatten_node(good)])  # type: ignore[arg-type]
        queries.merge_nodes(tx, "LearnerProfile", [bad_row])  # type: ignore[arg-type]

    with driver.session() as session:
        with pytest.raises((ClientError, TypeError, ValueError)):
            session.execute_write(_write_good_then_invalid)

    with driver.session() as session:
        count = session.run(
            "MATCH (l:LearnerProfile {id: $id}) RETURN count(l) AS c",
            id=good.id,
        ).single()["c"]
    assert count == 0, "an invalid payload must roll back the whole batch"


# ===========================================================================
# Test 8 - the database-level business key constraint actually fires
# ===========================================================================


def test_duplicate_natural_key_is_rejected_by_the_database(driver: Driver) -> None:
    """Two *different* nodes claiming the same natural key must be rejected.

    This is the failure the business-key constraints exist for, and it is a
    different thing from the idempotency MERGE guarantees. MERGE protects
    against the same record arriving twice under the same generated id.
    This protects against the same real-world learner arriving under two
    different ids - which is what an inconsistently-generated id upstream
    would look like, and which MERGE cannot catch because the ids differ.
    """
    initialize_schema(driver)

    shared_learner_id = _key("dup-natural-key")
    first = _learner("dup-a", learner_id=shared_learner_id)
    second = _learner(
        "dup-b",
        # deliberately a different node id, same natural key: exactly what a
        # buggy id generation upstream would produce
        id=node_id("LearnerProfile", _key("dup-natural-key-DIFFERENT")),
        learner_id=shared_learner_id,
    )
    assert first.id != second.id, "the point of this test is two distinct ids"

    load_graph(driver, LearnerGraph(generated_at=NOW, nodes=[first]))

    with pytest.raises(ClientError) as exc_info:
        load_graph(driver, LearnerGraph(generated_at=NOW, nodes=[second]))
    assert "constraint" in str(exc_info.value).lower()

    with driver.session() as session:
        count = session.run(
            "MATCH (l:LearnerProfile {learner_id: $lid}) RETURN count(l) AS c",
            lid=shared_learner_id,
        ).single()["c"]
    assert count == 1, "the rejected node must not have landed"


# ===========================================================================
# Test 9 - batch chunking
# ===========================================================================


def test_chunked_load_writes_every_row(driver: Driver) -> None:
    """A batch larger than the chunk size still lands in full, and stays
    idempotent when replayed."""
    learners = [_learner(f"chunk-{i}") for i in range(7)]
    graph = LearnerGraph(generated_at=NOW, nodes=list(learners))

    load_graph(driver, graph, batch_size=2)  # 7 rows over 4 chunks
    load_graph(driver, graph, batch_size=2)  # replay

    with driver.session() as session:
        count = session.run(
            "MATCH (l:LearnerProfile) WHERE l.id IN $ids RETURN count(l) AS c",
            ids=[x.id for x in learners],
        ).single()["c"]
    assert count == 7


def test_invalid_batch_size_is_rejected(driver: Driver) -> None:
    graph = LearnerGraph(generated_at=NOW, nodes=[_learner("badsize")])
    with pytest.raises(ValueError, match="batch size must be >= 1"):
        load_graph(driver, graph, batch_size=0)


# ===========================================================================
# Test 10 - the atomic variant covers the whole payload
# ===========================================================================


def test_load_graph_atomic_loads_nodes_and_edges(driver: Driver) -> None:
    learner = _learner("atomic")
    datasource = _review_datasource("atomic")
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

    load_graph_atomic(driver, graph)

    with driver.session() as session:
        count = session.run(
            "MATCH (l:LearnerProfile {id: $lid})-[:PRODUCED]->(:DataSource) "
            "RETURN count(*) AS c",
            lid=learner.id,
        ).single()["c"]
    assert count == 1


# ===========================================================================
# Test 11 - connection error handling
# ===========================================================================


def test_unreachable_uri_raises_graph_connection_error() -> None:
    """A bad URI must surface as this project's own error with a message
    that says what to check - not a bare driver exception."""
    from neo4j import GraphDatabase

    bad = GraphDatabase.driver("bolt://127.0.0.1:1", auth=("neo4j", "nope"))
    try:
        with pytest.raises(connections.GraphConnectionError, match="not reachable"):
            connections.verify_connection(bad)
    finally:
        bad.close()
