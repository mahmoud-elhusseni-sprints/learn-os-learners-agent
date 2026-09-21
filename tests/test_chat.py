from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from src.app.main import app
from src.app.schemas.agent_response import EmployerResponse
from src.app.services.agent_orchestration import (
    AgentTimeoutError,
    AgentUpstreamError,
)

client = TestClient(app)


def test_followup_endpoint_uses_real_graph_and_returns_real_visual():
    """Real API/DB/adapter/graph/renderer; only LLM and graph data are doubles."""
    from unittest.mock import Mock

    from langchain_core.messages import AIMessage

    from src.app.schemas.models import ToolResult

    user_id, headers = create_test_user()
    conversation = create_conversation(user_id, headers)
    model = Mock()
    model.bind_tools.return_value = model
    model.invoke.side_effect = [
        AIMessage(content="I can investigate this learner."),
        AIMessage(
            content="",
            tool_calls=[
                {"name": "get_skill_proofs", "args": {"skill": "python"}, "id": "proof"}
            ],
        ),
        AIMessage(content="One Python observation was retrieved."),
    ]
    with (
        patch(
            "src.app.agents.talent_intelligence.graph.get_chat_model",
            return_value=model,
        ),
        patch(
            "src.app.agents.talent_intelligence.tools.get_learner_profile",
            return_value=ToolResult("ok", {"learner_id": "L001"}),
        ),
        patch(
            "src.app.agents.talent_intelligence.tools._find_learner",
            return_value={"learner_id": "L001"},
        ),
        patch(
            "src.app.agents.talent_intelligence.tools.get_skill_proofs",
            return_value=ToolResult(
                "ok",
                [
                    {
                        "evidence_id": "offline-card",
                        "source_type": "review",
                        "observation": "Used Python",
                    }
                ],
            ),
        ) as proofs,
    ):
        initial = client.post(
            f"/conversations/{conversation}/chat",
            headers=headers,
            json={"content": "Investigate this learner", "learner_name_or_id": "L001"},
        )
        assert initial.status_code == 201
        followup = client.post(
            f"/conversations/{conversation}/chat",
            headers=headers,
            json={"content": "Chart their Python evidence"},
        )
    assert followup.status_code == 201
    proofs.assert_called_once_with("L001", "python")
    messages = model.invoke.call_args_list[1].args[0]
    assert [m.type for m in messages] == ["system", "human", "ai", "human"]
    assert messages[1].content == "Investigate this learner"
    assert messages[-1].content == "Chart their Python evidence"
    response = followup.json()["response"]
    assert response["fallback"] is None
    assert "<svg" in response["artifacts"][0]["data"]


def test_selection_survives_requests_and_is_isolated_and_rolled_back():
    user_id, headers = create_test_user()
    first = create_conversation(user_id, headers)
    second = create_conversation(user_id, headers)
    with patch(
        "src.app.services.conversation_service.AgentOrchestrationAdapter"
    ) as factory:
        respond = factory.return_value.respond
        respond.return_value = make_response("Evidence summary")

        def send(conversation, **payload):
            return client.post(
                f"/conversations/{conversation}/chat",
                headers=headers,
                json={"content": "What about their skills?", **payload},
            )

        assert send(first, learner_name_or_id="L001").status_code == 201
        assert send(first).status_code == 201
        assert respond.call_args.kwargs["learner_name_or_id"] == "L001"
        assert send(second).status_code == 201
        assert respond.call_args.kwargs["learner_name_or_id"] is None
        assert send(first, learner_name_or_id="L002").status_code == 201
        assert send(first).status_code == 201
        assert respond.call_args.kwargs["learner_name_or_id"] == "L002"
        respond.side_effect = AgentUpstreamError("Unavailable")
        assert send(first, learner_name_or_id="L003").status_code == 502
        respond.side_effect = None
        assert send(first).status_code == 201
        assert respond.call_args.kwargs["learner_name_or_id"] == "L002"


def create_test_user(name: str = "Chat Test User"):
    email = f"chat_{uuid4().hex}@example.com"
    password = "TestPassword123"

    signup_response = client.post(
        "/auth/signup",
        json={
            "name": name,
            "email": email,
            "password": password,
        },
    )

    assert signup_response.status_code == 201

    user_id = signup_response.json()["id"]

    signin_response = client.post(
        "/auth/signin",
        json={
            "email": email,
            "password": password,
        },
    )

    assert signin_response.status_code == 200

    token = signin_response.json()["access_token"]

    return user_id, {
        "Authorization": f"Bearer {token}",
    }


def make_response(markdown: str) -> EmployerResponse:
    return EmployerResponse(
        markdown=markdown,
        artifacts=[],
        fallback=None,
    )


def create_conversation(
    user_id: int,
    headers: dict[str, str],
) -> int:
    response = client.post(
        f"/users/{user_id}/conversations",
        headers=headers,
    )

    assert response.status_code == 201

    return response.json()["id"]


def get_messages(
    conversation_id: int,
    headers: dict[str, str],
) -> list[dict]:
    response = client.get(
        f"/conversations/{conversation_id}/messages",
        headers=headers,
    )

    assert response.status_code == 200

    return response.json()


def test_chat_persists_user_and_assistant_messages():
    user_id, headers = create_test_user()

    conversation_id = create_conversation(
        user_id,
        headers,
    )

    with patch(
        "src.app.services.conversation_service.AgentOrchestrationAdapter"
    ) as mock_adapter:
        mock_adapter.return_value.respond.return_value = make_response(
            "Python evidence was found in the learner records."
        )

        response = client.post(
            f"/conversations/{conversation_id}/chat",
            headers=headers,
            json={
                "content": "What evidence do we have for Python?",
                "learner_name_or_id": "L001",
            },
        )

    assert response.status_code == 201

    data = response.json()

    assert data["message"]["conversation_id"] == conversation_id
    assert data["message"]["sender_role"] == "assistant"
    assert (
        data["message"]["content"]
        == "Python evidence was found in the learner records."
    )

    assert (
        data["response"]["markdown"]
        == "Python evidence was found in the learner records."
    )

    assert data["response"]["artifacts"] == []
    assert data["response"]["fallback"] is None

    messages = get_messages(
        conversation_id,
        headers,
    )

    assert len(messages) == 2

    assert messages[0]["sender_role"] == "user"
    assert messages[0]["content"] == "What evidence do we have for Python?"

    assert messages[1]["sender_role"] == "assistant"
    assert messages[1]["content"] == "Python evidence was found in the learner records."


def test_chat_passes_previous_history_separately_from_current_message():
    user_id, headers = create_test_user()

    conversation_id = create_conversation(
        user_id,
        headers,
    )

    with patch(
        "src.app.services.conversation_service.AgentOrchestrationAdapter"
    ) as mock_adapter:
        mock_adapter.return_value.respond.return_value = make_response("First answer")

        first_response = client.post(
            f"/conversations/{conversation_id}/chat",
            headers=headers,
            json={
                "content": "Tell me about Python.",
                "learner_name_or_id": "L001",
            },
        )

        assert first_response.status_code == 201

        mock_adapter.return_value.respond.return_value = make_response("Second answer")

        second_response = client.post(
            f"/conversations/{conversation_id}/chat",
            headers=headers,
            json={
                "content": "What about the recent evidence?",
                "learner_name_or_id": "L001",
            },
        )

        assert second_response.status_code == 201

        calls = mock_adapter.return_value.respond.call_args_list

    assert len(calls) == 2

    second_call = calls[1]

    assert second_call.args[0] == "What about the recent evidence?"

    assert second_call.kwargs["learner_name_or_id"] == "L001"

    assert second_call.kwargs["history"] == [
        {
            "role": "user",
            "content": "Tell me about Python.",
        },
        {
            "role": "assistant",
            "content": "First answer",
        },
    ]


def test_first_chat_has_empty_history():
    user_id, headers = create_test_user()

    conversation_id = create_conversation(
        user_id,
        headers,
    )

    with patch(
        "src.app.services.conversation_service.AgentOrchestrationAdapter"
    ) as mock_adapter:
        mock_adapter.return_value.respond.return_value = make_response("First answer")

        response = client.post(
            f"/conversations/{conversation_id}/chat",
            headers=headers,
            json={
                "content": "Tell me about Python.",
            },
        )

        assert response.status_code == 201

        mock_adapter.return_value.respond.assert_called_once()

        call = mock_adapter.return_value.respond.call_args

    assert call.args[0] == "Tell me about Python."
    assert call.kwargs["history"] == []
    assert call.kwargs["learner_name_or_id"] is None


def test_chat_can_use_different_learners_in_same_conversation():
    user_id, headers = create_test_user()

    conversation_id = create_conversation(
        user_id,
        headers,
    )

    with patch(
        "src.app.services.conversation_service.AgentOrchestrationAdapter"
    ) as mock_adapter:
        mock_adapter.return_value.respond.return_value = make_response(
            "Learner L001 answer"
        )

        first_response = client.post(
            f"/conversations/{conversation_id}/chat",
            headers=headers,
            json={
                "content": "What is L001's Python experience?",
                "learner_name_or_id": "L001",
            },
        )

        assert first_response.status_code == 201

        mock_adapter.return_value.respond.return_value = make_response(
            "Learner L002 answer"
        )

        second_response = client.post(
            f"/conversations/{conversation_id}/chat",
            headers=headers,
            json={
                "content": "What is L002's Python experience?",
                "learner_name_or_id": "L002",
            },
        )

        assert second_response.status_code == 201

        calls = mock_adapter.return_value.respond.call_args_list

    assert len(calls) == 2

    assert calls[0].kwargs["learner_name_or_id"] == "L001"
    assert calls[1].kwargs["learner_name_or_id"] == "L002"


def test_chat_validates_conversation_before_agent_run():
    _, headers = create_test_user()

    with patch(
        "src.app.services.conversation_service.AgentOrchestrationAdapter"
    ) as mock_adapter:
        response = client.post(
            "/conversations/999999/chat",
            headers=headers,
            json={
                "content": "This should fail.",
                "learner_name_or_id": "L001",
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"

    mock_adapter.assert_not_called()


def test_user_cannot_chat_in_another_users_conversation():
    alice_id, alice_headers = create_test_user("Alice")
    _, bob_headers = create_test_user("Bob")

    conversation_id = create_conversation(
        alice_id,
        alice_headers,
    )

    with patch(
        "src.app.services.conversation_service.AgentOrchestrationAdapter"
    ) as mock_adapter:
        response = client.post(
            f"/conversations/{conversation_id}/chat",
            headers=bob_headers,
            json={
                "content": "Bob should not access this.",
                "learner_name_or_id": "L001",
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"

    mock_adapter.assert_not_called()


def test_chat_requires_authentication():
    response = client.post(
        "/conversations/999999/chat",
        json={
            "content": "Hello",
            "learner_name_or_id": "L001",
        },
    )

    assert response.status_code == 401


def test_chat_validation_requires_content():
    _, headers = create_test_user()

    response = client.post(
        "/conversations/999999/chat",
        headers=headers,
        json={
            "learner_name_or_id": "L001",
        },
    )

    assert response.status_code == 422


def test_agent_timeout_returns_504():
    user_id, headers = create_test_user()

    conversation_id = create_conversation(
        user_id,
        headers,
    )

    with patch(
        "src.app.services.conversation_service.AgentOrchestrationAdapter"
    ) as mock_adapter:
        mock_adapter.return_value.respond.side_effect = AgentTimeoutError(
            "The Talent Intelligence Agent timed out."
        )

        response = client.post(
            f"/conversations/{conversation_id}/chat",
            headers=headers,
            json={
                "content": "Check Python evidence.",
                "learner_name_or_id": "L001",
            },
        )

    assert response.status_code == 504
    assert "timed out" in response.json()["detail"]


def test_agent_upstream_failure_returns_502():
    user_id, headers = create_test_user()

    conversation_id = create_conversation(
        user_id,
        headers,
    )

    with patch(
        "src.app.services.conversation_service.AgentOrchestrationAdapter"
    ) as mock_adapter:
        mock_adapter.return_value.respond.side_effect = AgentUpstreamError(
            "The Talent Intelligence Agent could not process the request."
        )

        response = client.post(
            f"/conversations/{conversation_id}/chat",
            headers=headers,
            json={
                "content": "Check Python evidence.",
                "learner_name_or_id": "L001",
            },
        )

    assert response.status_code == 502
    assert "could not process" in response.json()["detail"]


def test_agent_failure_does_not_persist_messages():
    user_id, headers = create_test_user()

    conversation_id = create_conversation(
        user_id,
        headers,
    )

    with patch(
        "src.app.services.conversation_service.AgentOrchestrationAdapter"
    ) as mock_adapter:
        mock_adapter.return_value.respond.side_effect = AgentUpstreamError(
            "The Talent Intelligence Agent could not process the request."
        )

        response = client.post(
            f"/conversations/{conversation_id}/chat",
            headers=headers,
            json={
                "content": "This should not be persisted.",
                "learner_name_or_id": "L001",
            },
        )

    assert response.status_code == 502

    messages = get_messages(
        conversation_id,
        headers,
    )

    assert messages == []


def test_chat_preserves_structured_agent_response():
    user_id, headers = create_test_user()

    conversation_id = create_conversation(
        user_id,
        headers,
    )

    structured_response = EmployerResponse(
        markdown="Python evidence was found.",
        artifacts=[],
        fallback=None,
    )

    with patch(
        "src.app.services.conversation_service.AgentOrchestrationAdapter"
    ) as mock_adapter:
        mock_adapter.return_value.respond.return_value = structured_response

        response = client.post(
            f"/conversations/{conversation_id}/chat",
            headers=headers,
            json={
                "content": "Show me Python evidence.",
                "learner_name_or_id": "L001",
            },
        )

    assert response.status_code == 201

    data = response.json()

    assert data["response"]["markdown"] == "Python evidence was found."
    assert data["response"]["artifacts"] == []
    assert data["response"]["fallback"] is None

    assert data["message"]["content"] == "Python evidence was found."
