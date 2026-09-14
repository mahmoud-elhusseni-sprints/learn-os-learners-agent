"""Storage boundary checks and an explicitly enabled synthetic Neo4j smoke test."""

import os
from datetime import UTC, datetime
from unittest.mock import MagicMock, Mock
from uuid import uuid4

import pytest

from src.app.models.models import LearnerProfile, MetricDraft
from src.app.repositories.periodic_profiles import (
    ConcurrentProfileUpdate,
    Neo4jProfileStorage,
)
from src.app.services.periodic_profiles import Snapshot


def repository(tx):
    driver = MagicMock()
    session = driver.session.return_value.__enter__.return_value
    session.execute_write.side_effect = lambda callback: callback(tx)
    return Neo4jProfileStorage(driver)


def test_atomic_save_preserves_raw_untouched_metric():
    raw = '{"docker":{"summary":"old","confidence":0.5,"custom":"keep"}}'
    profile = LearnerProfile(
        metrics={"docker": {"summary": "old", "confidence": 0.5, "custom": "keep"}}
    )
    snapshot = Snapshot(profile, raw, None, 0)
    tx = Mock()
    tx.run.side_effect = [[{"metrics": raw, "version": 0, "checkpoint": None}], Mock()]
    repository(tx).save("a", snapshot, profile, datetime.now(UTC))
    import json

    assert json.loads(tx.run.call_args.kwargs["metrics"]) == json.loads(raw)
    assert tx.run.call_args.kwargs["version"] == 1
    assert "checkpoint" in tx.run.call_args.kwargs


def test_stale_save_is_rejected_before_write():
    tx = Mock()
    tx.run.return_value = [{"metrics": "{}", "version": 2, "checkpoint": None}]
    profile = LearnerProfile()
    with pytest.raises(ConcurrentProfileUpdate):
        repository(tx).save(
            "a", Snapshot(profile, "{}", None, 0), profile, datetime.now(UTC)
        )
    assert tx.run.call_count == 1


@pytest.mark.skipif(
    os.getenv("TASK14_NEO4J_TEST") != "1", reason="Explicit live test opt-in"
)
def test_real_neo4j_atomic_checkpoint():
    from src.app.agents.learner_profile_update.agent import LearnerProfileUpdateAgent
    from src.app.graph.connections import get_driver
    from src.app.services.periodic_profiles import update_learner

    driver = get_driver()
    learner_id = "task14-test-" + str(uuid4())
    try:
        with driver.session() as session:
            session.run(
                "CREATE (:LearnerProfile {learner_id:$id, is_active:true})",
                id=learner_id,
            ).consume()
        repo = Neo4jProfileStorage(driver)
        assert learner_id in repo.active_ids()
        initial = repo.load(learner_id)
        assert initial is not None
        assert repo.cards(learner_id) == []
        now = datetime.now(UTC)
        repo.save(learner_id, initial, initial.profile, now)
        updated = repo.load(learner_id)
        assert updated.checkpoint == now.isoformat()
        assert updated.version == 1
        with pytest.raises(ConcurrentProfileUpdate):
            repo.save(learner_id, initial, initial.profile, now)
        with driver.session() as session:
            session.run(
                "MATCH (l:LearnerProfile {learner_id:$id}) "
                "CREATE (l)-[:HAS_MEMORY_CARD]->(:MemoryCard {card_id:$id, "
                "metric_key:'python', content:'Completed a reviewed exercise', "
                "rationale:'Review', tags:['technical_skills'], "
                "created_at:datetime('2026-01-01T00:00:00Z')})",
                id=learner_id,
            ).consume()
        synth = Mock()
        synth.synthesize.return_value = MetricDraft(
            summary="Reviewed exercise", confidence=0.6
        )
        outcome = update_learner(learner_id, repo, LearnerProfileUpdateAgent(synth))
        assert outcome["card_count"] == 1
        assert repo.load(learner_id).profile.metrics["python"].evidence_ids == [
            learner_id
        ]
    finally:
        with driver.session() as session:
            session.run(
                "MATCH (m:MemoryCard {card_id:$id}) DETACH DELETE m", id=learner_id
            ).consume()
            session.run(
                "MATCH (l:LearnerProfile {learner_id:$id}) DELETE l", id=learner_id
            ).consume()
