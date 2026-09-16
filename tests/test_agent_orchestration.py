from unittest.mock import Mock

import pytest

from src.app.services.agent_orchestration import (
    AgentOrchestrationAdapter,
    AgentTimeoutError,
    AgentUpstreamError,
)


def test_format_history():
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hello! How can I help?"},
        {"role": "user", "content": "Tell me about Python experience."},
    ]

    formatted = AgentOrchestrationAdapter.format_history(history)

    assert "Previous conversation:" in formatted
    assert "User: Hello" in formatted
    assert "Assistant: Hello! How can I help?" in formatted
    assert "User: Tell me about Python experience." in formatted


def test_format_empty_history():
    result = AgentOrchestrationAdapter.format_history([])

    assert result == ""


def test_respond_calls_agent_with_message_and_history():
    mock_agent = Mock()
    mock_agent.respond.return_value = "Agent response"

    adapter = AgentOrchestrationAdapter(agent=mock_agent)

    history = [
        {"role": "user", "content": "Previous question"},
        {"role": "assistant", "content": "Previous answer"},
    ]

    result = adapter.respond(
        "Current question",
        history=history,
        learner_name_or_id="L001",
    )

    assert result == "Agent response"

    mock_agent.respond.assert_called_once()

    call_args, call_kwargs = mock_agent.respond.call_args

    assert "Previous conversation:" in call_args[0]
    assert "User: Previous question" in call_args[0]
    assert "Assistant: Previous answer" in call_args[0]
    assert "Current user message:" in call_args[0]
    assert "Current question" in call_args[0]

    assert call_kwargs["learner_name_or_id"] == "L001"


def test_respond_without_history():
    mock_agent = Mock()
    mock_agent.respond.return_value = "Agent response"

    adapter = AgentOrchestrationAdapter(agent=mock_agent)

    result = adapter.respond("Hello")

    assert result == "Agent response"

    mock_agent.respond.assert_called_once_with(
        "Hello",
        learner_name_or_id=None,
    )


def test_timeout_is_converted_to_agent_timeout_error():
    mock_agent = Mock()
    mock_agent.respond.side_effect = TimeoutError()

    adapter = AgentOrchestrationAdapter(agent=mock_agent)

    with pytest.raises(AgentTimeoutError, match="timed out"):
        adapter.respond("Hello")


def test_agent_failure_is_converted_to_upstream_error():
    mock_agent = Mock()
    mock_agent.respond.side_effect = RuntimeError("Neo4j unavailable")

    adapter = AgentOrchestrationAdapter(agent=mock_agent)

    with pytest.raises(
        AgentUpstreamError,
        match="could not process the request",
    ):
        adapter.respond("Hello")