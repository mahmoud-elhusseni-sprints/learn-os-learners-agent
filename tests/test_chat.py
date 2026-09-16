from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from src.app.main import app

client = TestClient(app)


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


def test_chat_persists_user_and_assistant_messages():
    user_id, headers = create_test_user()

    conversation_response = client.post(
        f"/users/{user_id}/conversations",
        headers=headers,
    )

    assert conversation_response.status_code == 201

    conversation_id = conversation_response.json()["id"]

    with patch(
        "src.app.services.conversation_service.AgentOrchestrationAdapter"
    ) as mock_adapter:
        mock_adapter.return_value.respond.return_value = (
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

    assert data["conversation_id"] == conversation_id
    assert data["sender_role"] == "assistant"
    assert (
        data["content"]
        == "Python evidence was found in the learner records."
    )

    messages_response = client.get(
        f"/conversations/{conversation_id}/messages",
        headers=headers,
    )

    assert messages_response.status_code == 200

    messages = messages_response.json()

    assert len(messages) == 2

    assert messages[0]["sender_role"] == "user"
    assert messages[0]["content"] == "What evidence do we have for Python?"

    assert messages[1]["sender_role"] == "assistant"
    assert (
        messages[1]["content"]
        == "Python evidence was found in the learner records."
    )


def test_chat_passes_previous_history_to_agent():
    user_id, headers = create_test_user()

    conversation_response = client.post(
        f"/users/{user_id}/conversations",
        headers=headers,
    )

    assert conversation_response.status_code == 201

    conversation_id = conversation_response.json()["id"]

    with patch(
        "src.app.services.conversation_service.AgentOrchestrationAdapter"
    ) as mock_adapter:
        mock_adapter.return_value.respond.return_value = "First answer"

        first_response = client.post(
            f"/conversations/{conversation_id}/chat",
            headers=headers,
            json={
                "content": "Tell me about Python.",
                "learner_name_or_id": "L001",
            },
        )

        assert first_response.status_code == 201

        mock_adapter.return_value.respond.return_value = "Second answer"

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

    history = second_call.kwargs["history"]

    assert history == [
        {
            "role": "user",
            "content": "Tell me about Python.",
        },
        {
            "role": "assistant",
            "content": "First answer",
        },
    ]

    assert second_call.args[0] == "What about the recent evidence?"
    assert second_call.kwargs["learner_name_or_id"] == "L001"


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

    conversation_response = client.post(
        f"/users/{alice_id}/conversations",
        headers=alice_headers,
    )

    assert conversation_response.status_code == 201

    conversation_id = conversation_response.json()["id"]

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

    conversation_response = client.post(
        f"/users/{user_id}/conversations",
        headers=headers,
    )

    conversation_id = conversation_response.json()["id"]

    with patch(
        "src.app.services.conversation_service.AgentOrchestrationAdapter"
    ) as mock_adapter:
        from src.app.services.agent_orchestration import AgentTimeoutError

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

    conversation_response = client.post(
        f"/users/{user_id}/conversations",
        headers=headers,
    )

    conversation_id = conversation_response.json()["id"]

    with patch(
        "src.app.services.conversation_service.AgentOrchestrationAdapter"
    ) as mock_adapter:
        from src.app.services.agent_orchestration import AgentUpstreamError

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