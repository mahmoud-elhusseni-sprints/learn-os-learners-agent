"""Synthetic, offline contract/regression tests for Task 10."""

import json
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.agents.learner_profile_update.agent import (
    LearnerProfileUpdateAgent,
    LLMMetricSynthesizer,
    ProfileUpdateError,
)
from app.agents.learner_profile_update.prompts import SYSTEM_PROMPT, build_metric_input
from src.app.models.models import (
    LearnerProfile,
    MemoryCard,
    MetricDraft,
    ProfileUpdateInput,
)


def make_card(card_id="new", metric_key="python", **changes):
    return MemoryCard.model_validate(
        {
            "card_id": card_id,
            "meeting_id": None,
            "metric_key": metric_key,
            "content": "The review records passing Python unit tests.",
            "rationale": "The reviewer explicitly reports the tests passed.",
            "tags": ["technical_skills"],
            "created_at": "2026-09-01T12:00:00Z",
            **changes,
        }
    )


@pytest.fixture
def baseline():
    return LearnerProfile.model_validate(
        {
            "learner_id": "synthetic-learner",
            "name": "Example Learner",
            "metadata": {"nested": [1, {"preserve": True}]},
            "metrics": {
                "python": {
                    "summary": "Previously needed help with testing.",
                    "confidence": 0.4,
                    "evidence_ids": ["old"],
                    "custom_metadata": {"keep": [1, 2]},
                },
                "communication": {
                    "summary": "Explained one design decision.",
                    "confidence": 0.6,
                    "evidence_ids": ["comm-old"],
                    "custom_metadata": {"keep": [3]},
                },
            },
        }
    )


@pytest.fixture
def synthesizer():
    fake = Mock()
    fake.synthesize.return_value = MetricDraft(
        summary=(
            "Prior testing difficulties remain context; [new] reports passing tests."
        ),
        confidence=0.65,
    )
    return fake


@pytest.mark.parametrize("previous", [None, LearnerProfile()])
def test_initial_profile_contains_only_observed_metrics(previous, synthesizer):
    result = LearnerProfileUpdateAgent(synthesizer).update(
        ProfileUpdateInput(previous_profile=previous, memory_cards=[make_card()])
    )
    assert set(result.metrics) == {"python"}
    assert result.metrics["python"].evidence_ids == ["new"]
    assert result.model_extra == {}


def test_single_metric_preserves_untouched_objects_and_input(baseline, synthesizer):
    before = baseline.model_dump_json()
    untouched = baseline.metrics["communication"].model_dump_json()
    request = ProfileUpdateInput(previous_profile=baseline, memory_cards=[make_card()])
    result = LearnerProfileUpdateAgent(synthesizer).update(request)
    assert baseline.model_dump_json() == before
    assert result.metrics["communication"].model_dump_json() == untouched
    assert result.metrics["communication"] is not baseline.metrics["communication"]
    assert result.metrics["python"].evidence_ids == ["old", "new"]
    assert result.metrics["python"].custom_metadata == {"keep": [1, 2]}
    assert result.model_extra == baseline.model_extra
    args = synthesizer.synthesize.call_args.args
    assert args[1].summary == baseline.metrics["python"].summary
    assert args[1].confidence == 0.4


def test_multiple_targets_and_tags_do_not_create_metrics(baseline, synthesizer):
    result = LearnerProfileUpdateAgent(synthesizer).update(
        ProfileUpdateInput(
            previous_profile=baseline,
            memory_cards=[
                make_card(tags=["leadership", "docker"]),
                make_card("card-2", "sql"),
            ],
        )
    )
    assert set(result.metrics) == {"python", "communication", "sql"}
    assert result.metrics["sql"].evidence_ids == ["card-2"]
    assert synthesizer.synthesize.call_count == 2


@pytest.mark.parametrize("previous", [None, LearnerProfile()])
def test_no_cards_no_model_call(previous, synthesizer):
    result = LearnerProfileUpdateAgent(synthesizer).update(
        ProfileUpdateInput(previous_profile=previous)
    )
    assert result.metrics == {}
    synthesizer.synthesize.assert_not_called()


def test_no_cards_preserves_populated_profile(baseline, synthesizer):
    result = LearnerProfileUpdateAgent(synthesizer).update(
        ProfileUpdateInput(previous_profile=baseline)
    )
    assert result.model_dump_json() == baseline.model_dump_json()
    synthesizer.synthesize.assert_not_called()


def test_duplicate_cards_and_replay_do_not_inflate_evidence(baseline, synthesizer):
    agent = LearnerProfileUpdateAgent(synthesizer)
    result = agent.update(
        ProfileUpdateInput(
            previous_profile=baseline, memory_cards=[make_card(), make_card()]
        )
    )
    assert len(synthesizer.synthesize.call_args.args[2]) == 1
    assert result.metrics["python"].evidence_ids == ["old", "new"]
    synthesizer.reset_mock()
    replay = agent.update(
        ProfileUpdateInput(previous_profile=result, memory_cards=[make_card()])
    )
    assert replay == result
    synthesizer.synthesize.assert_not_called()


def test_conflicting_duplicate_ids_rejected_before_model_call(synthesizer):
    with pytest.raises(ProfileUpdateError, match="share a card_id"):
        LearnerProfileUpdateAgent(synthesizer).update(
            ProfileUpdateInput(
                memory_cards=[make_card(), make_card(content="Different content")]
            )
        )
    synthesizer.synthesize.assert_not_called()


def test_cards_sorted_by_actual_timestamp(baseline, synthesizer):
    LearnerProfileUpdateAgent(synthesizer).update(
        ProfileUpdateInput(
            previous_profile=baseline,
            memory_cards=[
                make_card("later", created_at="2026-09-01T10:00:00Z"),
                make_card("earlier", created_at="2026-09-01T11:00:00+03:00"),
            ],
        )
    )
    assert [c.card_id for c in synthesizer.synthesize.call_args.args[2]] == [
        "earlier",
        "later",
    ]


def test_failure_is_atomic_and_safe(baseline, synthesizer):
    before = baseline.model_dump_json()
    synthesizer.synthesize.side_effect = [
        MetricDraft(summary="Valid first update", confidence=0.5),
        RuntimeError("secret-private-error"),
    ]
    with pytest.raises(ProfileUpdateError) as error:
        LearnerProfileUpdateAgent(synthesizer).update(
            ProfileUpdateInput(
                previous_profile=baseline,
                memory_cards=[make_card(), make_card("two", "communication")],
            )
        )
    assert "secret-private-error" not in str(error.value)
    assert baseline.model_dump_json() == before


def test_mutating_adapter_cannot_modify_input_or_evidence_ids(baseline, synthesizer):
    before = baseline.model_dump_json()

    def mutate(key, previous, cards):
        previous.evidence_ids.append("invented")
        cards[0].card_id = "invented"
        return MetricDraft(summary="Observed test result", confidence=0.5)

    synthesizer.synthesize.side_effect = mutate
    result = LearnerProfileUpdateAgent(synthesizer).update(
        ProfileUpdateInput(previous_profile=baseline, memory_cards=[make_card()])
    )
    assert result.metrics["python"].evidence_ids == ["old", "new"]
    assert baseline.model_dump_json() == before


def test_invalid_constructed_model_is_revalidated(synthesizer):
    synthesizer.synthesize.return_value = MetricDraft.model_construct(
        summary="Invalid", confidence=20
    )
    with pytest.raises(ProfileUpdateError):
        LearnerProfileUpdateAgent(synthesizer).update(
            ProfileUpdateInput(memory_cards=[make_card()])
        )


@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan"), float("inf"), True, "0.5"])
def test_confidence_validation(value):
    with pytest.raises(ValidationError):
        MetricDraft(summary="Summary", confidence=value)


@pytest.mark.parametrize(
    "changes",
    [
        {"metric_key": " "},
        {"content": ""},
        {"created_at": "invalid"},
        {"created_at": "2026-09-01T12:00:00"},
        {"extra_field": "not allowed"},
    ],
)
def test_card_contract_rejects_invalid_inputs(changes):
    with pytest.raises(ValidationError):
        make_card(**changes)


def test_uuid_and_nullable_meeting_contract():
    identifier = uuid4()
    assert make_card(card_id=identifier).card_id == str(identifier)
    assert make_card(meeting_id=identifier).meeting_id == str(identifier)
    assert make_card().meeting_id is None
    assert {
        "card_id",
        "meeting_id",
        "metric_key",
        "content",
        "rationale",
        "tags",
        "created_at",
    }.issubset(set(MemoryCard.model_fields))


def test_prompt_receives_prior_baseline_not_invented_history(baseline):
    payload = json.loads(
        build_metric_input("python", baseline.metrics["python"], [make_card()])
    )
    assert payload["prior_summary"] == baseline.metrics["python"].summary
    assert payload["prior_summary_date"] is None
    assert "communication" not in payload
    assert payload["memory_cards"][0]["created_at"]
    for rule in (
        "Tags are descriptive",
        "contextual conflicts",
        "untrusted evidence",
        "not raw historical evidence",
        "Insufficient evidence",
    ):
        assert rule in SYSTEM_PROMPT


def test_adapter_requests_structured_output_and_validates():
    generator = Mock(
        return_value=MetricDraft(summary="[new] records passing tests.", confidence=0.6)
    )
    adapter = LLMMetricSynthesizer("test-model", generator)
    result = adapter.synthesize("python", None, [make_card()])
    assert result.confidence == 0.6
    kwargs = generator.call_args.kwargs
    assert kwargs["schema_model"] is MetricDraft
    assert kwargs["schema_name"] == "metric_update"
    assert kwargs["messages"][0]["content"] == SYSTEM_PROMPT


@pytest.mark.parametrize(
    "response",
    [
        ValueError("not JSON"),
        ValueError("empty"),
        ValueError("invalid confidence"),
        ValueError("unexpected field"),
        ValueError("truncated"),
        ValueError("refused"),
    ],
)
def test_adapter_fails_closed(response):
    generator = Mock(side_effect=response)
    with pytest.raises(ProfileUpdateError):
        LLMMetricSynthesizer("test", generator).synthesize(
            "python", None, [make_card()]
        )


def test_adapter_does_not_expose_provider_secrets():
    generator = Mock(side_effect=RuntimeError("secret-key"))
    with pytest.raises(ProfileUpdateError) as error:
        LLMMetricSynthesizer("test", generator).synthesize(
            "python", None, [make_card()]
        )
    assert "secret-key" not in str(error.value)


def test_from_env_requires_configuration(tmp_path, monkeypatch):
    monkeypatch.setattr("app.agents.learner_profile_update.agent.LITE_LLM_KEY", None)
    monkeypatch.setattr(
        "app.agents.learner_profile_update.agent.LITELLM_BASE_URL", None
    )
    monkeypatch.setattr("app.agents.learner_profile_update.agent.PRIMARY_MODEL", None)
    monkeypatch.setattr("app.agents.learner_profile_update.agent.AI_MODEL", None)
    with pytest.raises(ProfileUpdateError, match="Configure"):
        LLMMetricSynthesizer.from_env()
