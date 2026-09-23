import json
from unittest.mock import Mock, patch

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from src.app.agents.talent_intelligence import tools
from src.app.agents.talent_intelligence.agent import TalentIntelligenceAgent
from src.app.graph.helpers import get_command, run_command
from src.app.schemas.models import ToolResult


@pytest.fixture
def scripted_model(monkeypatch):
    """Script only the model; execute the real graph, handlers and serialization.

    These unit cases verify dispatch, not a live model's language understanding.
    Unexpected database access fails immediately rather than falling back silently.
    """
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setattr("src.app.core.llm_client.DEFAULT_API_KEY", "")
    monkeypatch.setattr(tools, "_find_learner", lambda target: {"learner_id": target})
    monkeypatch.setattr(
        tools,
        "_run",
        Mock(side_effect=AssertionError("Unexpected database call")),
    )

    def configure(name, arguments, answer="Insufficient evidence"):
        model = Mock()
        model.bind_tools.return_value = model
        model.invoke.side_effect = [
            AIMessage(
                content="",
                tool_calls=[{"name": name, "args": arguments, "id": "unit-call"}],
            ),
            AIMessage(content=answer),
        ]
        monkeypatch.setattr(
            "src.app.agents.talent_intelligence.graph.get_chat_model", lambda: model
        )
        return model

    return configure


def assert_tool_result(model, expected_status):
    assert model.invoke.call_count == 2
    returned = model.invoke.call_args.args[0][-1]
    assert isinstance(returned, ToolMessage)
    assert returned.tool_call_id == "unit-call"
    payload = json.loads(returned.content)
    assert payload["status"] == expected_status
    return payload


def test_registry_exposes_employer_commands():
    assert get_command("investigate_employer") is tools.investigate_employer
    assert get_command("suggest_next_steps") is tools.suggest_next_steps
    assert get_command("find_learners_with_skill") is tools.find_learners_with_skill
    assert get_command("search_evidence") is tools.search_evidence
    assert get_command("get_review_outcomes") is tools.get_review_outcomes
    assert get_command("get_assessment_results") is tools.get_assessment_results


def test_unknown_command_is_safe():
    result = run_command("not_a_command")
    assert result.status == "error"
    assert result.data is None


def test_investigation_deduplicates_direct_and_derived_cards():
    row = {
        "evidence_id": "card-1",
        "metric_key": "digital_ai_skills.python",
        "observation": "Used Python",
        "date": "2026-08-01",
        "learner_id": "learner-1",
    }
    with patch.object(tools, "_run", return_value=[row]):
        result = tools.investigate_employer("learner-1", "Python")

    assert result.status == "ok"
    assert [item["evidence_id"] for item in result.data] == ["card-1"]


def test_investigation_missing_focus_returns_insufficient_evidence():
    with patch.object(tools, "_run", return_value=[]):
        result = tools.investigate_employer("missing", "Kubernetes")

    assert result.status == "insufficient_evidence"
    assert result.data == []


def test_search_evidence_normalizes_rows_and_passes_filters():
    row = {
        "evidence_id": "card-1",
        "metric_key": "digital_ai_skills.python",
        "observation": "Used Python",
        "date": "2026-08-01",
        "tags": ["technical_skills"],
    }
    with patch.object(tools, "_run", return_value=[row]) as run:
        result = tools.search_evidence(
            "learner-1",
            "Python",
            "review",
            "2026-01-01",
            "2026-12-31",
            500,
        )

    assert result.status == "ok"
    assert result.data[0]["evidence_id"] == "card-1"
    params = run.call_args.kwargs
    assert params == {
        "learner_id": "learner-1",
        "query": "python",
        "source_type": "review",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "limit": 100,
    }


def test_review_outcomes_parse_payload_json():
    with patch.object(
        tools,
        "_run",
        return_value=[
            {
                "event_id": "review-1",
                "date": "2026-08-01",
                "payload_json": '{"task_headline":"API task","verdict":"passed"}',
            }
        ],
    ):
        result = tools.get_review_outcomes("learner-1")

    assert result.status == "ok"
    assert result.data[0]["task_headline"] == "API task"
    assert result.data[0]["verdict"] == "passed"


def test_assessment_results_support_legacy_datasource_name():
    with patch.object(
        tools,
        "_run",
        return_value=[
            {
                "event_id": "assessment-1",
                "date": "2026-08-02",
                "payload_json": (
                    '{"assessment_type":"post_course","score":8,'
                    '"max_score":10,"answers":[]}'
                ),
            }
        ],
    ):
        result = tools.get_assessment_results("learner-1")

    assert result.status == "ok"
    assert result.data[0]["score"] == 8
    assert result.data[0]["max_score"] == 10


def test_agent_routes_new_evidence_tools(scripted_model):
    model = scripted_model("get_review_outcomes", {}, "Observed review-1")
    agent = TalentIntelligenceAgent()
    agent.state.active_learner_id = "learner-1"
    with patch.object(
        tools,
        "get_review_outcomes",
        return_value=ToolResult(
            "ok",
            [
                {
                    "event_id": "review-1",
                    "date": "2026-08-01",
                    "task_headline": "API",
                    "verdict": "passed",
                }
            ],
        ),
    ) as get_reviews:
        answer = agent.respond("Show me the review outcomes")

    get_reviews.assert_called_once_with("learner-1")
    assert agent.state.last_tool_calls[-1]["tool"] == "get_review_outcomes"
    assert "review-1" in answer
    assert assert_tool_result(model, "ok")["data"][0]["event_id"] == "review-1"


def test_find_learners_with_skill_groups_and_orders_evidence():
    rows = [
        {
            "learner_id": "learner-1",
            "name": "Learner One",
            "evidence_id": "card-1",
            "observation": "Used Python",
            "date": "2026-08-01",
        },
        {
            "learner_id": "learner-2",
            "name": "Learner Two",
            "evidence_id": "card-2",
            "observation": "Built a Python service",
            "date": "2026-08-02",
        },
        {
            "learner_id": "learner-2",
            "name": "Learner Two",
            "evidence_id": "card-3",
            "observation": "Tested Python code",
            "date": "2026-08-01",
        },
    ]
    with patch.object(tools, "_run", return_value=rows):
        result = tools.find_learners_with_skill("Python")

    assert result.status == "ok"
    assert [item["name"] for item in result.data] == [
        "Learner Two",
        "Learner One",
    ]
    assert result.data[0]["evidence_count"] == 2


def test_agent_routes_cross_learner_skill_question_without_active_learner(
    scripted_model,
):
    model = scripted_model(
        "find_learners_with_skill", {"skill": "python"}, "Compare evidence coverage"
    )
    agent = TalentIntelligenceAgent()
    with patch.object(
        tools,
        "find_learners_with_skill",
        return_value=ToolResult(
            "ok",
            [
                {
                    "learner_id": "learner-1",
                    "name": "Learner One",
                    "evidence_count": 1,
                    "most_recent_date": "2026-08-01",
                    "evidence": [],
                }
            ],
        ),
    ) as find_learners:
        answer = agent.respond("Which learner has the strongest evidence in Python?")

    find_learners.assert_called_once_with("python")
    assert agent.state.last_tool_calls[-1]["tool"] == "find_learners_with_skill"
    assert "evidence coverage" in answer
    assert assert_tool_result(model, "ok")["data"][0]["learner_id"] == "learner-1"


def test_agent_passes_model_skill_from_hiring_question(scripted_model):
    model = scripted_model("find_learners_with_skill", {"skill": "python"})
    agent = TalentIntelligenceAgent()
    with patch.object(
        tools,
        "find_learners_with_skill",
        return_value=ToolResult("insufficient_evidence", []),
    ) as find_learners:
        agent.respond(
            "Which should I employ for my company if I need a Python developer?"
        )

    find_learners.assert_called_once_with("python")
    assert_tool_result(model, "insufficient_evidence")


def test_agent_passes_model_skill_after_hiring_context(scripted_model):
    model = scripted_model("find_learners_with_skill", {"skill": "python"})
    agent = TalentIntelligenceAgent()
    with patch.object(
        tools,
        "find_learners_with_skill",
        return_value=ToolResult("insufficient_evidence", []),
    ) as find_learners:
        agent.respond("Which should I hire in my company if I need a Python developer?")

    find_learners.assert_called_once_with("python")
    assert_tool_result(model, "insufficient_evidence")


def test_next_steps_are_derived_from_coverage_gaps():
    source = ToolResult(
        "ok",
        {
            "strengths": [],
            "gaps": [{"area": "behavioral_engagement", "reason": "missing"}],
        },
    )
    with patch.object(tools, "get_strengths_and_gaps", return_value=source):
        result = tools.suggest_next_steps("learner-1")

    assert result.status == "ok"
    assert result.data[0]["area"] == "behavioral_engagement"
    assert "Collect" in result.data[0]["action"]


def test_agent_routes_investigation_command(scripted_model):
    model = scripted_model(
        "investigate_employer", {"focus": "Investigate their recent work"}
    )
    agent = TalentIntelligenceAgent()
    agent.state.active_learner_id = "learner-1"
    with patch.object(
        tools,
        "investigate_employer",
        return_value=ToolResult("insufficient_evidence", []),
    ) as investigate:
        agent.respond("Investigate their recent work")

    investigate.assert_called_once_with("learner-1", "Investigate their recent work")
    assert agent.state.last_tool_calls[-1]["tool"] == "investigate_employer"
    assert_tool_result(model, "insufficient_evidence")


def test_agent_routes_next_steps_command(scripted_model):
    model = scripted_model("suggest_next_steps", {}, "Collect more evidence")
    agent = TalentIntelligenceAgent()
    agent.state.active_learner_id = "learner-1"
    with patch.object(
        tools,
        "suggest_next_steps",
        return_value=ToolResult(
            "ok", [{"area": "testing", "action": "Collect", "reason": "gap"}]
        ),
    ) as suggest:
        answer = agent.respond("What are the next steps?")

    suggest.assert_called_once_with("learner-1")
    assert agent.state.last_tool_calls[-1]["tool"] == "suggest_next_steps"
    assert "Collect" in answer
    assert assert_tool_result(model, "ok")["data"][0]["action"] == "Collect"


def test_agent_routes_canonical_taxonomy_tags_to_behavioral_context(scripted_model):
    model = scripted_model("get_behavioral_context", {})
    agent = TalentIntelligenceAgent()
    agent.state.active_learner_id = "learner-1"
    with patch.object(
        tools,
        "get_behavioral_context",
        return_value=ToolResult("insufficient_evidence", []),
    ) as get_behavior:
        agent.respond("What evidence shows teamwork collaboration?")

    get_behavior.assert_called_once_with("learner-1")
    assert_tool_result(model, "insufficient_evidence")
