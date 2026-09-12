from unittest.mock import patch

from src.app.agents.talent_intelligence import tools
from src.app.agents.talent_intelligence.agent import TalentIntelligenceAgent
from src.app.graph.helpers import get_command, run_command
from src.app.models.models import ToolResult


def test_registry_exposes_employer_commands():
    assert get_command("investigate_employer") is tools.investigate_employer
    assert get_command("suggest_next_steps") is tools.suggest_next_steps


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


def test_agent_routes_investigation_command():
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


def test_agent_routes_next_steps_command():
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
