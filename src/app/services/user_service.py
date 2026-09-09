from sqlalchemy.orm import Session

from src.app.repositories import user_repository
from src.app.schemas.user import UserCreate


def create_user(db: Session, user_data: UserCreate):
    existing_user = user_repository.get_user_by_email(
        db,
        user_data.email,
    )

    if existing_user:
        raise ValueError("A user with this email already exists")

    return user_repository.create_user(
        db,
        user_data,
    )


def get_users(db: Session):
    return user_repository.get_users(db)


def get_user_by_id(db: Session, user_id: int):
    return user_repository.get_user_by_id(
        db,
        user_id,
    )