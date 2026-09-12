
from uuid import uuid4

from fastapi.testclient import TestClient

from src.app.main import app
from datetime import datetime, timedelta, timezone

import jwt
from src.app.core.config import JWT_ALGORITHM, JWT_SECRET_KEY

client = TestClient(app)


def unique_email(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}@example.com"


def test_signup():
    email = unique_email("auth_signup")

    response = client.post(
        "/auth/signup",
        json={
            "name": "Auth Test User",
            "email": email,
            "password": "TestPassword123",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Auth Test User"
    assert data["email"] == email
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

    assert "password" not in data
    assert "password_hash" not in data


def test_signup_duplicate_email():
    email = unique_email("auth_duplicate")

    first_response = client.post(
        "/auth/signup",
        json={
            "name": "First Auth User",
            "email": email,
            "password": "TestPassword123",
        },
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/auth/signup",
        json={
            "name": "Second Auth User",
            "email": email,
            "password": "TestPassword123",
        },
    )

    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "A user with this email already exists"
    )



def test_signin():
    email = unique_email("auth_signin")

    signup_response = client.post(
        "/auth/signup",
        json={
            "name": "Signin Test User",
            "email": email,
            "password": "TestPassword123",
        },
    )

    assert signup_response.status_code == 201

    response = client.post(
        "/auth/signin",
        json={
            "email": email,
            "password": "TestPassword123",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["access_token"]


def test_signin_wrong_password():
    email = unique_email("auth_wrong_password")

    signup_response = client.post(
        "/auth/signup",
        json={
            "name": "Wrong Password User",
            "email": email,
            "password": "TestPassword123",
        },
    )

    assert signup_response.status_code == 201

    response = client.post(
        "/auth/signin",
        json={
            "email": email,
            "password": "WrongPassword123",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_protected_route_with_valid_token():
    email = unique_email("auth_protected")

    signup_response = client.post(
        "/auth/signup",
        json={
            "name": "Protected Route User",
            "email": email,
            "password": "TestPassword123",
        },
    )

    assert signup_response.status_code == 201

    user_id = signup_response.json()["id"]

    signin_response = client.post(
        "/auth/signin",
        json={
            "email": email,
            "password": "TestPassword123",
        },
    )

    assert signin_response.status_code == 200

    token = signin_response.json()["access_token"]

    response = client.get(
        f"/users/{user_id}/conversations",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200


def test_protected_route_without_token():
    response = client.get("/users/13/conversations")

    assert response.status_code == 401

def test_protected_route_with_invalid_token():
    response = client.get(
        "/users/13/conversations",
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_protected_route_with_expired_token():
    expired_token = jwt.encode(
        {
            "sub": "13",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    response = client.get(
        "/users/13/conversations",
        headers={
            "Authorization": f"Bearer {expired_token}",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"