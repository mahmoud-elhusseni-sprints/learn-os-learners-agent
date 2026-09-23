"""Offline Task 19 contracts, grounding, routing and timeout regression tests."""

import base64
import time
from threading import Event
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from src.app.agents.talent_intelligence.agent import TalentIntelligenceAgent
from src.app.agents.talent_intelligence import tools
from src.app.agents.talent_intelligence.visual_delegation import delegate, visual_intent
from src.app.schemas.agent_response import EmployerResponse, VisualOptions
from src.app.schemas.models import ToolResult, VisualizationFormat

RECORD = {
    "evidence_id": "card-1",
    "source_type": "review",
    "observation": "Used Python",
    "date": "2026-09-01",
}


@pytest.mark.parametrize(
    "query,intent",
    [
        ("What is their name?", "none"),
        ("Show a chart", "coverage"),
        ("Compare evidence coverage", "coverage"),
        ("Show a timeline", "unsupported"),
        ("Skill trajectories", "unsupported"),
        ("Chart, but text only", "none"),
    ],
)
def test_intent(query, intent):
    assert visual_intent(query) == intent


@pytest.mark.parametrize("format", list(VisualizationFormat))
def test_real_renderer_serializes(format):
    result = delegate(
        "chart", "Factual text", [RECORD, RECORD], VisualOptions(format=format)
    )
    restored = EmployerResponse.model_validate_json(result.model_dump_json())
    assert restored.markdown == "Factual text"
    assert restored.fallback is None
    assert len(restored.artifacts[0].evidence) == 1
    assert "not proficiency" in restored.artifacts[0].commentary
    if format == VisualizationFormat.PNG:
        assert base64.b64decode(restored.artifacts[0].data).startswith(b"\x89PNG")


def test_counts_not_scores():
    from src.app.agents.visualizer.agent import VisualizerAgent

    renderer = Mock(wraps=VisualizerAgent())
    delegate("chart", "answer", [dict(RECORD, score=99), RECORD], renderer=renderer)
    request = renderer.visualize.call_args.args[0]
    assert request.data == [{"label": "review", "count": 1}]


@pytest.mark.parametrize(
    "records", [[], [{"score": 95}], [dict(RECORD, evidence_id="")]]
)
def test_missing_verified_evidence(records):
    renderer = Mock()
    response = delegate("chart", "answer", records, renderer=renderer)
    assert response.fallback.code == "insufficient_evidence"
    renderer.visualize.assert_not_called()


def test_unsupported_does_not_call_renderer():
    renderer = Mock()
    assert (
        delegate("timeline", "answer", [RECORD], renderer=renderer).fallback.code
        == "unsupported"
    )
    renderer.visualize.assert_not_called()


def test_exception_preserves_text():
    renderer = Mock()
    renderer.visualize.side_effect = RuntimeError("private error details")
    result = delegate("chart", "answer", [RECORD], renderer=renderer)
    assert result.markdown == "answer"
    assert result.fallback.code == "error"
    assert "private" not in result.model_dump_json()


def test_timeout_returns_without_waiting():
    release = Event()
    renderer = Mock()
    renderer.visualize.side_effect = lambda request: release.wait(2)
    try:
        start = time.monotonic()
        result = delegate("chart", "answer", [RECORD], renderer=renderer, timeout=0.02)
        assert time.monotonic() - start < 0.5
        assert result.markdown == "answer"
        assert result.fallback.code == "timeout"
    finally:
        release.set()


def test_invalid_options():
    with pytest.raises(ValidationError):
        VisualOptions(format="pdf")
    with pytest.raises(ValidationError):
        VisualOptions(theme={"primary": "javascript:bad"})


def test_agent_captures_only_current_successful_evidence():
    agent = TalentIntelligenceAgent()

    def loop(*args, **kwargs):
        agent._call("search_evidence", lambda: ToolResult("ok", [RECORD]))
        return "Verified text"

    with patch(
        "src.app.agents.talent_intelligence.agent.run_tool_loop", side_effect=loop
    ):
        result = agent.respond_structured("chart")
    assert result.artifacts
    with patch(
        "src.app.agents.talent_intelligence.agent.run_tool_loop",
        return_value="No evidence",
    ):
        result = agent.respond_structured("chart")
    assert not result.artifacts
    assert result.fallback.code == "insufficient_evidence"


def test_graph_failure_is_not_reported_as_missing_evidence():
    agent = TalentIntelligenceAgent()

    result = agent._call(
        "get_skill_proofs",
        lambda learner_id, skill: (_ for _ in ()).throw(
            RuntimeError("Neo4j unavailable")
        ),
        "learner-1",
        "python",
    )

    assert result.status == "error"
    assert result.data is None
    assert "Evidence retrieval failed" in result.message


def test_empty_graph_result_is_still_insufficient_evidence():
    with patch(
        "src.app.agents.talent_intelligence.tools._run",
        return_value=[],
    ):
        result = tools.get_skill_proofs("learner-1", "python")

    assert result.status == "insufficient_evidence"
    assert result.data == []


def test_failed_tool_not_charted():
    agent = TalentIntelligenceAgent()
    agent._call("search_evidence", lambda: ToolResult("error", [RECORD]))
    assert agent._visual_evidence == []


def test_conflicting_ids_rejected():
    result = delegate(
        "chart", "answer", [RECORD, dict(RECORD, observation="Different")]
    )
    assert result.fallback.code == "insufficient_evidence"


def test_busy_does_not_render():
    from src.app.agents.talent_intelligence import visual_delegation as module

    with patch.object(module, "_SLOTS") as slots:
        slots.acquire.return_value = False
        renderer = Mock()
        result = delegate("chart", "answer", [RECORD], renderer=renderer)
    assert result.fallback.code == "busy"
    renderer.visualize.assert_not_called()


def test_explicit_renderer_failure():
    from src.app.schemas.models import VisualizationResponse

    renderer = Mock()
    renderer.visualize.return_value = VisualizationResponse(
        success=False, format=VisualizationFormat.SVG, error="render failed"
    )
    result = delegate("chart", "answer", [RECORD], renderer=renderer)
    assert result.fallback.code == "error"
    assert result.markdown == "answer"
