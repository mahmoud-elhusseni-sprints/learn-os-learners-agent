import os
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

JWT_ALGORITHM = "HS256"


password_hash = PasswordHash.recommended()

DUMMY_PASSWORD_HASH = password_hash.hash("dummy-password-for-timing")


def get_jwt_secret_key() -> str:
    secret_key = os.getenv("JWT_SECRET_KEY")

    if not secret_key:
        raise RuntimeError("JWT_SECRET_KEY environment variable is not set")

    return secret_key


def get_jwt_expire_minutes() -> int:
    value = os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES")

    if not value:
        raise RuntimeError(
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES environment variable is not set"
        )

    try:
        minutes = int(value)
    except ValueError as exc:
        raise RuntimeError(
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be an integer"
        ) from exc

    if minutes <= 0:
        raise RuntimeError("JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be greater than 0")

    return minutes


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(user_id: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=get_jwt_expire_minutes()
    )

    payload = {
        "sub": str(user_id),
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        get_jwt_secret_key(),
        algorithm=JWT_ALGORITHM,
    )
