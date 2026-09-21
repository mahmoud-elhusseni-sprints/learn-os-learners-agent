from uuid import uuid4

from fastapi.testclient import TestClient

from src.app.main import app

client = TestClient(app)


def create_test_user(name: str = "Conversation Test User"):
    email = f"conversation_{uuid4().hex}@example.com"
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


def test_create_conversation():
    user_id, headers = create_test_user()

    response = client.post(
        f"/users/{user_id}/conversations",
        headers=headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["user_id"] == user_id
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_get_user_conversations():
    user_id, headers = create_test_user()

    create_response = client.post(
        f"/users/{user_id}/conversations",
        headers=headers,
    )

    assert create_response.status_code == 201

    response = client.get(
        f"/users/{user_id}/conversations",
        headers=headers,
    )

    assert response.status_code == 200

    conversations = response.json()

    assert isinstance(conversations, list)
    assert any(
        conversation["id"] == create_response.json()["id"]
        for conversation in conversations
    )


def test_create_conversation_for_nonexistent_user():
    _, headers = create_test_user()

    response = client.post(
        "/users/999999/conversations",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"


def test_create_conversation_without_token():
    user_id, _ = create_test_user()

    response = client.post(
        f"/users/{user_id}/conversations",
    )

    assert response.status_code == 401


def test_get_conversations_without_token():
    user_id, _ = create_test_user()

    response = client.get(
        f"/users/{user_id}/conversations",
    )

    assert response.status_code == 401


def test_user_cannot_access_another_users_conversations():
    alice_id, alice_headers = create_test_user("Alice")
    _, bob_headers = create_test_user("Bob")

    create_response = client.post(
        f"/users/{alice_id}/conversations",
        headers=alice_headers,
    )

    assert create_response.status_code == 201

    response = client.get(
        f"/users/{alice_id}/conversations",
        headers=bob_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"


def test_user_cannot_create_conversation_for_another_user():
    alice_id, _ = create_test_user("Alice")
    _, bob_headers = create_test_user("Bob")

    response = client.post(
        f"/users/{alice_id}/conversations",
        headers=bob_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"


def test_add_message():
    user_id, headers = create_test_user()

    conversation_response = client.post(
        f"/users/{user_id}/conversations",
        headers=headers,
    )

    assert conversation_response.status_code == 201

    conversation_id = conversation_response.json()["id"]

    response = client.post(
        f"/conversations/{conversation_id}/messages",
        headers=headers,
        json={
            "sender_role": "user",
            "content": "Hello from pytest.",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["conversation_id"] == conversation_id
    assert data["sender_role"] == "user"
    assert data["content"] == "Hello from pytest."
    assert "timestamp" in data


def test_get_conversation_messages_chronologically():
    user_id, headers = create_test_user()

    conversation_response = client.post(
        f"/users/{user_id}/conversations",
        headers=headers,
    )

    assert conversation_response.status_code == 201

    conversation_id = conversation_response.json()["id"]

    first_message = client.post(
        f"/conversations/{conversation_id}/messages",
        headers=headers,
        json={
            "sender_role": "user",
            "content": "First message",
        },
    )

    second_message = client.post(
        f"/conversations/{conversation_id}/messages",
        headers=headers,
        json={
            "sender_role": "assistant",
            "content": "Second message",
        },
    )

    assert first_message.status_code == 201
    assert second_message.status_code == 201

    response = client.get(
        f"/conversations/{conversation_id}/messages",
        headers=headers,
    )

    assert response.status_code == 200

    messages = response.json()

    assert len(messages) == 2
    assert messages[0]["content"] == "First message"
    assert messages[1]["content"] == "Second message"
    assert messages[0]["timestamp"] <= messages[1]["timestamp"]


def test_get_messages_for_nonexistent_conversation():
    _, headers = create_test_user()

    response = client.get(
        "/conversations/999999/messages",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"


def test_add_message_to_nonexistent_conversation():
    _, headers = create_test_user()

    response = client.post(
        "/conversations/999999/messages",
        headers=headers,
        json={
            "sender_role": "user",
            "content": "This should fail.",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"


def test_get_messages_without_token():
    user_id, headers = create_test_user()

    conversation_response = client.post(
        f"/users/{user_id}/conversations",
        headers=headers,
    )

    assert conversation_response.status_code == 201

    conversation_id = conversation_response.json()["id"]

    response = client.get(
        f"/conversations/{conversation_id}/messages",
    )

    assert response.status_code == 401


def test_add_message_without_token():
    user_id, headers = create_test_user()

    conversation_response = client.post(
        f"/users/{user_id}/conversations",
        headers=headers,
    )

    assert conversation_response.status_code == 201

    conversation_id = conversation_response.json()["id"]

    response = client.post(
        f"/conversations/{conversation_id}/messages",
        json={
            "sender_role": "user",
            "content": "This should fail.",
        },
    )

    assert response.status_code == 401


def test_user_cannot_access_another_users_messages():
    alice_id, alice_headers = create_test_user("Alice")
    _, bob_headers = create_test_user("Bob")

    conversation_response = client.post(
        f"/users/{alice_id}/conversations",
        headers=alice_headers,
    )

    assert conversation_response.status_code == 201

    conversation_id = conversation_response.json()["id"]

    message_response = client.post(
        f"/conversations/{conversation_id}/messages",
        headers=alice_headers,
        json={
            "sender_role": "user",
            "content": "Alice's private message",
        },
    )

    assert message_response.status_code == 201

    get_response = client.get(
        f"/conversations/{conversation_id}/messages",
        headers=bob_headers,
    )

    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "Conversation not found"


def test_user_cannot_add_message_to_another_users_conversation():
    alice_id, alice_headers = create_test_user("Alice")
    _, bob_headers = create_test_user("Bob")

    conversation_response = client.post(
        f"/users/{alice_id}/conversations",
        headers=alice_headers,
    )

    assert conversation_response.status_code == 201

    conversation_id = conversation_response.json()["id"]

    response = client.post(
        f"/conversations/{conversation_id}/messages",
        headers=bob_headers,
        json={
            "sender_role": "user",
            "content": "Bob should not access this.",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"


def test_message_validation():
    user_id, headers = create_test_user()

    conversation_response = client.post(
        f"/users/{user_id}/conversations",
        headers=headers,
    )

    assert conversation_response.status_code == 201

    conversation_id = conversation_response.json()["id"]

    response = client.post(
        f"/conversations/{conversation_id}/messages",
        headers=headers,
        json={
            "sender_role": "user",
        },
    )

    assert response.status_code == 422