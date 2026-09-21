from unittest.mock import Mock

import pytest

from src.app.schemas.agent_response import EmployerResponse
from src.app.services.agent_orchestration import (
    AgentOrchestrationAdapter,
    AgentTimeoutError,
    AgentUpstreamError,
)


def make_response(markdown: str = "Agent response") -> EmployerResponse:
    return EmployerResponse(
        markdown=markdown,
        artifacts=[],
        fallback=None,
    )


def test_format_history():
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hello! How can I help?"},
        {
            "role": "user",
            "content": "Tell me about Python experience.",
        },
    ]

    formatted = AgentOrchestrationAdapter.format_history(history)

    assert "Previous conversation:" in formatted
    assert "User: Hello" in formatted
    assert "Assistant: Hello! How can I help?" in formatted
    assert "User: Tell me about Python experience." in formatted


def test_format_empty_history():
    result = AgentOrchestrationAdapter.format_history([])

    assert result == ""


def test_respond_passes_current_message_and_formatted_history():
    mock_agent = Mock()
    mock_agent.respond_structured.return_value = make_response()

    adapter = AgentOrchestrationAdapter(agent=mock_agent)

    history = [
        {
            "role": "user",
            "content": "Previous question",
        },
        {
            "role": "assistant",
            "content": "Previous answer",
        },
    ]

    result = adapter.respond(
        "Current question",
        history=history,
        learner_name_or_id="L001",
    )

    assert result == make_response()

    mock_agent.respond_structured.assert_called_once_with(
        "Current question",
        history=(
            "Previous conversation:\n"
            "User: Previous question\n"
            "Assistant: Previous answer"
        ),
        learner_name_or_id="L001",
    )


def test_respond_does_not_prepend_history_to_current_message():
    mock_agent = Mock()
    mock_agent.respond_structured.return_value = make_response()

    adapter = AgentOrchestrationAdapter(agent=mock_agent)

    history = [
        {
            "role": "user",
            "content": "Tell me about Python.",
        },
        {
            "role": "assistant",
            "content": "Python evidence was found.",
        },
    ]

    adapter.respond(
        "What about the recent evidence?",
        history=history,
        learner_name_or_id="L001",
    )

    call_args, call_kwargs = mock_agent.respond_structured.call_args

    assert call_args[0] == "What about the recent evidence?"

    assert "Previous conversation:" not in call_args[0]
    assert "Tell me about Python." not in call_args[0]
    assert "Python evidence was found." not in call_args[0]

    assert call_kwargs["history"] == (
        "Previous conversation:\n"
        "User: Tell me about Python.\n"
        "Assistant: Python evidence was found."
    )

    assert call_kwargs["learner_name_or_id"] == "L001"


def test_respond_without_history():
    mock_agent = Mock()
    mock_agent.respond_structured.return_value = make_response()

    adapter = AgentOrchestrationAdapter(agent=mock_agent)

    result = adapter.respond("Hello")

    assert result == make_response()

    mock_agent.respond_structured.assert_called_once_with(
        "Hello",
        history="",
        learner_name_or_id=None,
    )


def test_respond_without_learner():
    mock_agent = Mock()
    mock_agent.respond_structured.return_value = make_response()

    adapter = AgentOrchestrationAdapter(agent=mock_agent)

    adapter.respond(
        "Compare the learners based on Python experience.",
        history=[],
    )

    mock_agent.respond_structured.assert_called_once_with(
        "Compare the learners based on Python experience.",
        history="",
        learner_name_or_id=None,
    )


def test_timeout_is_converted_to_agent_timeout_error():
    mock_agent = Mock()
    mock_agent.respond_structured.side_effect = TimeoutError()

    adapter = AgentOrchestrationAdapter(agent=mock_agent)

    with pytest.raises(
        AgentTimeoutError,
        match="timed out",
    ):
        adapter.respond("Hello")


def test_agent_failure_is_converted_to_upstream_error():
    mock_agent = Mock()
    mock_agent.respond_structured.side_effect = RuntimeError("Neo4j unavailable")

    adapter = AgentOrchestrationAdapter(agent=mock_agent)

    with pytest.raises(
        AgentUpstreamError,
        match="could not process the request",
    ):
        adapter.respond("Hello")
