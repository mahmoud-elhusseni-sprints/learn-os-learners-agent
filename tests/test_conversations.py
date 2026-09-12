from fastapi.testclient import TestClient

from src.app.main import app


client = TestClient(app)

TEST_EMAIL = "conversation_test@example.com"
TEST_PASSWORD = "TestPassword123"


def create_test_user():
    response = client.post(
        "/users",
        json={
            "name": "Conversation Test User",
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )

    # If the user already exists from a previous test run,
    # retrieve it instead.
    if response.status_code == 400:
        users_response = client.get("/users")
        assert users_response.status_code == 200

        users = users_response.json()

        for user in users:
            if user["email"] == TEST_EMAIL:
                return user["id"]

    assert response.status_code == 201
    return response.json()["id"]


def get_auth_headers():
    response = client.post(
        "/auth/signin",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 200

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }


def test_create_conversation():
    user_id = create_test_user()

    response = client.post(
        f"/users/{user_id}/conversations",
    )

    assert response.status_code == 201

    data = response.json()

    assert data["user_id"] == user_id
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_get_user_conversations():
    user_id = create_test_user()

    create_response = client.post(
        f"/users/{user_id}/conversations",
    )

    assert create_response.status_code == 201

    response = client.get(
        f"/users/{user_id}/conversations",
        headers=get_auth_headers(),
    )

    assert response.status_code == 200

    conversations = response.json()

    assert isinstance(conversations, list)
    assert any(
        conversation["id"] == create_response.json()["id"]
        for conversation in conversations
    )


def test_create_conversation_for_nonexistent_user():
    response = client.post(
        "/users/999999/conversations",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_add_message():
    user_id = create_test_user()

    conversation_response = client.post(
        f"/users/{user_id}/conversations",
    )

    assert conversation_response.status_code == 201

    conversation_id = conversation_response.json()["id"]

    response = client.post(
        f"/conversations/{conversation_id}/messages",
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
    user_id = create_test_user()

    conversation_response = client.post(
        f"/users/{user_id}/conversations",
    )

    assert conversation_response.status_code == 201

    conversation_id = conversation_response.json()["id"]

    first_message = client.post(
        f"/conversations/{conversation_id}/messages",
        json={
            "sender_role": "user",
            "content": "First message",
        },
    )

    second_message = client.post(
        f"/conversations/{conversation_id}/messages",
        json={
            "sender_role": "assistant",
            "content": "Second message",
        },
    )

    assert first_message.status_code == 201
    assert second_message.status_code == 201

    response = client.get(
        f"/conversations/{conversation_id}/messages",
    )

    assert response.status_code == 200

    messages = response.json()

    assert len(messages) == 2
    assert messages[0]["content"] == "First message"
    assert messages[1]["content"] == "Second message"
    assert messages[0]["timestamp"] <= messages[1]["timestamp"]


def test_get_messages_for_nonexistent_conversation():
    response = client.get(
        "/conversations/999999/messages",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"


def test_add_message_to_nonexistent_conversation():
    response = client.post(
        "/conversations/999999/messages",
        json={
            "sender_role": "user",
            "content": "This should fail.",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"


def test_message_validation():
    user_id = create_test_user()

    conversation_response = client.post(
        f"/users/{user_id}/conversations",
    )

    assert conversation_response.status_code == 201

    conversation_id = conversation_response.json()["id"]

    response = client.post(
        f"/conversations/{conversation_id}/messages",
        json={
            "sender_role": "user",
        },
    )

    assert response.status_code == 422