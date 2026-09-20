from uuid import uuid4

from fastapi.testclient import TestClient

from src.app.main import app

client = TestClient(app)


def unique_email(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}@example.com"


def signup_user(name: str = "Test User") -> tuple[str, int, str]:
    email = unique_email("pytest_user")

    response = client.post(
        "/auth/signup",
        json={
            "name": name,
            "email": email,
            "password": "TestPassword123",
        },
    )

    assert response.status_code == 201

    user_id = response.json()["id"]

    signin_response = client.post(
        "/auth/signin",
        json={
            "email": email,
            "password": "TestPassword123",
        },
    )

    assert signin_response.status_code == 200

    token = signin_response.json()["access_token"]

    return email, user_id, token


def test_get_user_by_id():
    email, user_id, token = signup_user("Get User Test")

    response = client.get(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == user_id
    assert response.json()["name"] == "Get User Test"
    assert response.json()["email"] == email


def test_get_user_without_token():
    _, user_id, _ = signup_user()

    response = client.get(f"/users/{user_id}")

    assert response.status_code == 401


def test_get_nonexistent_user():
    _, _, token = signup_user()

    response = client.get(
        "/users/999999",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_get_another_user():
    _, _, first_token = signup_user("First User")
    _, second_user_id, _ = signup_user("Second User")

    response = client.get(
        f"/users/{second_user_id}",
        headers={"Authorization": f"Bearer {first_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"
