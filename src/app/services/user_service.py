from sqlalchemy.orm import Session

from src.app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    hash_password,
    verify_password,
)
from src.app.models.user import User
from src.app.repositories import user_repository
from src.app.schemas.auth import SignupRequest


def signup(
    db: Session,
    signup_data: SignupRequest,
)-> User:
    email = str(signup_data.email).lower()

    existing_user = user_repository.get_user_by_email(
        db,
        email,
    )

    if existing_user:
        raise ValueError("A user with this email already exists")

    password_hash = hash_password(signup_data.password)

    return user_repository.create_auth_user(
        db,
        name=signup_data.name,
        email=email,
        password_hash=password_hash,
    )


def signin(
    db: Session,
    email: str,
    password: str,
)-> str:
    email = email.lower()

    user = user_repository.get_user_by_email(
        db,
        email,
    )

    if user is None or user.password_hash is None:
        verify_password(
            password,
            DUMMY_PASSWORD_HASH,
        )
        raise ValueError("Invalid email or password")

    if not verify_password(
        password,
        user.password_hash,
    ):
        raise ValueError("Invalid email or password")

    return create_access_token(user.id)



def get_user_by_id(
    db: Session,
    user_id: int,
) -> User | None:
    return user_repository.get_user_by_id(
        db,
        user_id,
    )
