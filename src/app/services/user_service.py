from sqlalchemy.orm import Session

from src.app.core.security import hash_password
from src.app.repositories import user_repository
from src.app.schemas.auth import SignupRequest
from src.app.schemas.user import UserCreate
from src.app.core.security import hash_password, verify_password, create_access_token

def create_user(db: Session, user_data: UserCreate):
    existing_user = user_repository.get_user_by_email(
        db,
        user_data.email,
    )

    if existing_user:
        raise ValueError("A user with this email already exists")

    password_hash = hash_password(user_data.password)

    return user_repository.create_auth_user(
        db,
        name=user_data.name,
        email=user_data.email,
        password_hash=password_hash,
    )


def signup(db: Session, signup_data: SignupRequest):
    existing_user = user_repository.get_user_by_email(
        db,
        signup_data.email,
    )

    if existing_user:
        raise ValueError("A user with this email already exists")

    password_hash = hash_password(signup_data.password)

    return user_repository.create_auth_user(
        db,
        name=signup_data.name,
        email=signup_data.email,
        password_hash=password_hash,
    )

def signin(db: Session, email: str, password: str):
    user = user_repository.get_user_by_email(db, email)

    if user is None or not verify_password(password, user.password_hash):
        raise ValueError("Invalid email or password")

    return create_access_token(user.id)


def get_users(db: Session):
    return user_repository.get_users(db)


def get_user_by_id(db: Session, user_id: int):
    return user_repository.get_user_by_id(
        db,
        user_id,
    )