"""Offline regressions for the Task 6 review; no model/API calls required."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.agents.talent_intelligence import tools
from app.agents.talent_intelligence.agent import TalentIntelligenceAgent
from app.agents.talent_intelligence.llm_adapter import (
    LOOP_FAILURE,
    LiteLLMGeminiAdapter,
)
from app.agents.talent_intelligence.models import ToolResult


@pytest.mark.parametrize(
    "question,skill",
    [
        ("What are the learner's strongest Python contributions?", "python"),
        (
            "Give an overview of their experience with machine learning",
            "machine learning",
        ),
        ("Do they have experience with distributed systems?", "distributed systems"),
        ("What is their Python history?", "python"),
        ("Have they worked with FastAPI?", "fastapi"),
    ],
)
def test_specific_skill_routes_to_skill_evidence(question, skill):
    agent = TalentIntelligenceAgent()
    agent.state.active_learner_id = "learner"
    with patch.object(
        tools, "get_skill_proofs", return_value=ToolResult("insufficient_evidence", [])
    ) as lookup:
        agent.respond(question)
    lookup.assert_called_once_with("learner", skill)
    assert agent.state.last_tool_calls[-1]["tool"] == "get_skill_proofs"


def test_skill_matching_uses_word_boundaries():
    assert TalentIntelligenceAgent._extract_skill("Give a paragraph overview") is None


@pytest.mark.parametrize(
    "question,tool",
    [
        ("What is their history?", "get_milestone_history"),
        ("What are their strengths?", "get_strengths_and_gaps"),
        ("How is their communication?", "get_behavioral_context"),
        ("Do they know Python?", "get_skill_proofs"),
        ("Show their profile", "get_learner_profile"),
    ],
)
def test_tool_failures_are_safe_and_tracked(question, tool):
    agent = TalentIntelligenceAgent()
    agent.state.active_learner_id = "learner"
    with patch.object(tools, tool, side_effect=ValueError("private data")):
        answer = agent.respond(question)
    assert "retrieval failed" in answer
    assert "private data" not in answer
    assert "Insufficient evidence" not in answer
    assert agent.state.last_tool_calls[-1]["status"] == "error"
    assert agent.state.last_tool_calls[-1]["evidence_ids"] == []


def test_failed_learner_switch_clears_previous_identity():
    agent = TalentIntelligenceAgent()
    agent.state.active_learner_id = "previous"
    with patch.object(tools, "get_learner_profile", side_effect=OSError):
        answer = agent.respond("Show profile", "new learner")
    assert "retrieval failed" in answer
    assert agent.state.active_learner_id is None


def card(card_id, metric, content):
    return {
        "card_id": card_id,
        "learner_id": "learner",
        "metric_key": metric,
        "normalized_payload": {"content": content},
    }


def test_strengths_exclude_blockers_assignments_and_negative_observations():
    records = [
        card("blocker", "internship_context.current_blockers", "The API went down."),
        card("assignment", "learning_goals.learner_tasks", "Assigned Python work."),
        card(
            "negative",
            "behavioral_engagement.engagement",
            "Has not demonstrated engagement.",
        ),
        card(
            "positive",
            "behavioral_engagement.effort_signals",
            "Demonstrated problem-solving effort by adapting to an API outage.",
        ),
    ]
    with patch.object(
        tools,
        "_load_jsonl",
        side_effect=lambda name: (
            tuple(records) if name == "meeting_memory_cards.jsonl" else ()
        ),
    ):
        result = tools.get_strengths_and_gaps("learner")
    assert [s["evidence_ids"] for s in result.data["strengths"]] == [["positive"]]
    assert all(g["status"] == "insufficient_evidence" for g in result.data["gaps"])
    assert "behavioral_engagement.adaptability" in {
        g["area"] for g in result.data["gaps"]
    }


def test_real_blocker_records_are_not_strengths():
    result = tools.get_strengths_and_gaps("900353f6-f011-4d31-9a8a-b050b891c69c")
    assert result.status == "ok"
    assert all(
        s["area"] != "internship_context.current_blockers"
        for s in result.data["strengths"]
    )


@pytest.mark.parametrize(
    "content,calls,expected",
    [
        (None, True, LOOP_FAILURE),
        ("Insufficient evidence", False, "Insufficient evidence"),
        (None, False, "Unable to complete"),
    ],
)
def test_loop_failure_is_not_missing_evidence(content, calls, expected):
    adapter = object.__new__(LiteLLMGeminiAdapter)
    adapter._settings = {
        "AI_AGENT_URL": "https://example.invalid",
        "AI_API_KEY": "fake",
        "AI_MODEL": "fake",
    }
    call = SimpleNamespace(
        id="call", function=SimpleNamespace(name="get_learner_profile", arguments="{}")
    )
    message = Mock()
    message.tool_calls = [call] if calls else []
    message.content = content
    message.model_dump.return_value = {"role": "assistant"}
    completion = SimpleNamespace(choices=[SimpleNamespace(message=message)])
    with patch("openai.OpenAI") as client:
        create = client.return_value.chat.completions.create
        create.return_value = completion
        answer = adapter.run_tool_loop(
            "Profile?", {"get_learner_profile": lambda _: {"status": "ok", "data": {}}}
        )
    assert expected in answer
    assert create.call_count == (3 if calls else 1)
