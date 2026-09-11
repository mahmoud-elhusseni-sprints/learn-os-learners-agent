from __future__ import annotations

import uuid

import pytest
from neo4j.exceptions import ConfigurationError, ServiceUnavailable

from src.app.agents.talent_intelligence import tools
from src.app.graph import connections


@pytest.fixture(scope="module")
def graph_driver():
    try:
        driver = connections.get_driver()
        driver.verify_connectivity()
    except (ConfigurationError, ServiceUnavailable):
        pytest.skip("Neo4j is not reachable - run `docker compose up -d neo4j` first")
    yield driver
    connections.close_driver()


def test_investigation_follows_both_graph_paths_and_deduplicates(graph_driver):
    suffix = uuid.uuid4().hex
    learner_id = f"integration-{suffix}"
    datasource_id = f"source-{suffix}"
    card_id = f"card-{suffix}"
    try:
        with graph_driver.session() as session:
            session.run(
                "CREATE (l:LearnerProfile {learner_id: $learner_id, "
                "name: 'Integration'})"
                "CREATE (d:DataSource {datasource_id: $datasource_id})"
                "CREATE (m:MemoryCard {card_id: $card_id, metric_key: 'python', "
                "content: 'Used Python', created_at: '2026-08-01'})"
                "CREATE (l)-[:PRODUCED]->(d)-[:EXTRACTED_INTO]->(m)"
                "CREATE (l)-[:HAS_MEMORY_CARD]->(m)",
                learner_id=learner_id,
                datasource_id=datasource_id,
                card_id=card_id,
            ).consume()

        result = tools.investigate_employer(learner_id, "python")
        assert result.status == "ok"
        assert [item["evidence_id"] for item in result.data] == [card_id]
    finally:
        with graph_driver.session() as session:
            session.run(
                "MATCH (l:LearnerProfile {learner_id: $learner_id}) DETACH DELETE l",
                learner_id=learner_id,
            ).consume()
            session.run(
                "MATCH (d:DataSource {datasource_id: $datasource_id}) DETACH DELETE d",
                datasource_id=datasource_id,
            ).consume()
            session.run(
                "MATCH (m:MemoryCard {card_id: $card_id}) DETACH DELETE m",
                card_id=card_id,
            ).consume()


def test_investigation_missing_learner_is_insufficient(graph_driver):
    result = tools.investigate_employer("does-not-exist", "python")
    assert result.status == "insufficient_evidence"
    assert result.data == []
