"""Task 14 regression tests; no live broker, database, or model needed."""

import json
from copy import deepcopy
from datetime import UTC, datetime
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import pytest

from src.app.agents.learner_profile_update.agent import LearnerProfileUpdateAgent
from src.app.models.models import LearnerProfile, MemoryCard, MetricDraft, ProfileMetric
from src.app.services.periodic_profiles import Snapshot, update_learner
from src.app.workers import profile_updates as tasks
from src.app.workers.celery_app import app

NOW = datetime(2026, 9, 14, tzinfo=UTC)


def card(card_id="c1", metric="python", date="2026-09-01T00:00:00Z"):
    return MemoryCard(
        card_id=card_id,
        metric_key=metric,
        content="Completed exercise",
        rationale="Reviewed work",
        tags=[],
        created_at=date,
    )


class Store:
    def __init__(self):
        self.snapshot = Snapshot(LearnerProfile(learner_id="a"), "{}", None, 0)
        self.rows = [card()]
        self.saved = []

    def load(self, learner_id):
        return deepcopy(self.snapshot)

    def cards(self, learner_id):
        return self.rows

    def save(self, learner_id, snapshot, profile, cutoff):
        self.saved.append(deepcopy(profile))
        self.snapshot = Snapshot(
            profile,
            json.dumps(profile.model_dump(mode="json")["metrics"]),
            cutoff.isoformat(),
            snapshot.version + 1,
        )


def make_agent():
    synthesizer = Mock()
    synthesizer.synthesize.return_value = MetricDraft(
        summary="Reviewed exercise", confidence=0.6
    )
    return LearnerProfileUpdateAgent(synthesizer)


def test_first_run_and_repeated_run():
    store = Store()
    assert update_learner("a", store, make_agent(), NOW)["card_count"] == 1
    assert store.saved[-1].metrics["python"].evidence_ids == ["c1"]
    assert update_learner("a", store, make_agent(), NOW)["card_count"] == 0


def test_late_cards_and_future_cards():
    store = Store()
    update_learner("a", store, make_agent(), NOW)
    store.rows += [
        card("late", date="2026-08-01T00:00:00Z"),
        card("future", date="2027-01-01T00:00:00Z"),
    ]
    assert update_learner("a", store, make_agent(), NOW)["card_count"] == 1
    assert store.saved[-1].metrics["python"].evidence_ids == ["c1", "late"]


def test_untargeted_preserved():
    store = Store()
    metric = ProfileMetric(summary="Existing", confidence=0.4, evidence_ids=["old"])
    store.snapshot.profile.metrics["docker"] = metric
    update_learner("a", store, make_agent(), NOW)
    assert store.saved[-1].metrics["docker"] == metric


def test_agent_failure_does_not_save():
    store = Store()
    broken = Mock()
    broken.update.side_effect = RuntimeError("model unavailable")
    with pytest.raises(RuntimeError):
        update_learner("a", store, broken, NOW)
    assert store.saved == []
    assert store.snapshot.checkpoint is None


def test_missing_date_fails_without_save():
    store = Store()
    store.rows = [card(date=None)]
    with pytest.raises(ValueError):
        update_learner("a", store, make_agent(), NOW)
    assert not store.saved


def test_no_cards_skips_model():
    store = Store()
    store.rows = []
    model = Mock()
    assert update_learner("a", store, model, NOW)["status"] == "no_new_cards"
    model.update.assert_not_called()
    assert store.snapshot.checkpoint == NOW.isoformat()


def test_inactive_skips_save():
    store = Store()
    store.snapshot = None
    assert update_learner("a", store, Mock(), NOW)["status"] == "inactive"
    assert not store.saved


def test_weekly_schedule():
    schedule = app.conf.beat_schedule["weekly-profile-updates"]
    assert schedule["task"] == "profiles.dispatch"
    assert schedule["schedule"].hour == {3}
    assert schedule["schedule"].minute == {0}
    assert schedule["schedule"].day_of_week == {0}
    assert app.conf.timezone == "Africa/Cairo"
    assert (
        datetime(2026, 1, 4, 3, tzinfo=ZoneInfo(app.conf.timezone)).utcoffset().seconds
        == 7200
    )
    assert (
        datetime(2026, 7, 5, 3, tzinfo=ZoneInfo(app.conf.timezone)).utcoffset().seconds
        == 10800
    )


def test_dispatch_continues_after_publish_failure():
    repo = Mock()
    repo.active_ids.return_value = ["bad", "good"]
    with (
        patch.object(tasks, "storage", return_value=repo),
        patch.object(
            tasks.update, "delay", side_effect=[RuntimeError("broker"), None]
        ) as publish,
        patch.object(tasks.dispatch, "retry", side_effect=RuntimeError("retry")),
    ):
        with pytest.raises(RuntimeError):
            tasks.dispatch.run()
    assert publish.call_count == 2


def test_task_executes_with_mock_storage():
    store = Store()
    with (
        patch.object(tasks, "storage", return_value=store),
        patch.object(tasks, "agent", return_value=make_agent()),
    ):
        result = tasks.update.apply(args=["a"], throw=True)
    assert result.result["status"] == "updated"


def test_task_retries_without_persistence():
    store = Store()
    with (
        patch.object(tasks, "storage", return_value=store),
        patch.object(tasks, "agent", side_effect=RuntimeError("offline")),
        patch.object(tasks.update, "retry", side_effect=RuntimeError("retry")) as retry,
    ):
        with pytest.raises(RuntimeError):
            tasks.update.run("a")
    assert retry.call_args.kwargs["countdown"] == tasks.RETRY_SECONDS
    assert not store.saved


def test_retries_are_bounded_and_next_learner_can_succeed():
    store = Store()
    with (
        patch.object(tasks, "storage", return_value=store),
        patch.object(tasks, "agent", side_effect=RuntimeError("offline")) as factory,
    ):
        result = tasks.update.apply(args=["a"], throw=False)
    assert result.failed()
    assert factory.call_count == tasks.MAX_RETRIES + 1
    assert not store.saved
    with (
        patch.object(tasks, "storage", return_value=store),
        patch.object(tasks, "agent", return_value=make_agent()),
    ):
        assert tasks.update.apply(args=["b"], throw=True).successful()


def test_unsafe_agent_output_rejected():
    store = Store()
    bad = Mock()
    profile = store.snapshot.profile.model_copy(deep=True)
    profile.metrics["unrequested"] = ProfileMetric(summary="Invented", confidence=0.4)
    bad.update.return_value = profile
    with pytest.raises(ValueError, match="untargeted"):
        update_learner("a", store, bad, NOW)
    assert not store.saved
