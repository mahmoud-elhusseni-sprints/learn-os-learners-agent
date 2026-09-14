from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.models.user import User


def create_auth_user(
    db: Session,
    name: str,
    email: str,
    password_hash: str,
) -> User:
    user = User(
        name=name,
        email=email,
        password_hash=password_hash,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user



def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    return db.scalar(statement)
