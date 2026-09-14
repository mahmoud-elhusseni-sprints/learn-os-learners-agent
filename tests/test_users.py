from uuid import uuid4

from fastapi.testclient import TestClient

from src.app.main import app


client = TestClient(app)


def unique_email(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}@example.com"


def test_create_user():
    email = unique_email("pytest_user")

    response = client.post(
        "/users",
        json={
            "name": "Pytest User",
            "email": email,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Pytest User"
    assert data["email"] == email
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_get_users():
    response = client.get("/users")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_user_by_id():
    email = unique_email("get_user_test")

    create_response = client.post(
        "/users",
        json={
            "name": "Get User Test",
            "email": email,
        },
    )

    assert create_response.status_code == 201

    user_id = create_response.json()["id"]

    response = client.get(f"/users/{user_id}")

    assert response.status_code == 200
    assert response.json()["id"] == user_id
    assert response.json()["name"] == "Get User Test"


def test_get_nonexistent_user():
    response = client.get("/users/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_create_user_validation_error():
    response = client.post(
        "/users",
        json={
            "name": "Invalid User",
        },
    )

    assert response.status_code == 422


def test_duplicate_email():
    email = unique_email("duplicate_test")

    first_response = client.post(
        "/users",
        json={
            "name": "First User",
            "email": email,
        },
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/users",
        json={
            "name": "Second User",
            "email": email,
        },
    )

    assert second_response.status_code == 400
    assert second_response.json()["detail"] == (
        "A user with this email already exists"
    )
