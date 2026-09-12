import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from src.app.core.config import JWT_ALGORITHM, JWT_SECRET_KEY
from src.app.database.connection import get_db
from src.app.models.user import User
from src.app.repositories import user_repository


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/signin",
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )

        subject = payload.get("sub")

        if subject is None:
            raise credentials_exception

        user_id = int(subject)

    except (jwt.InvalidTokenError, ValueError):
        raise credentials_exception

    user = user_repository.get_user_by_id(
        db,
        user_id,
    )

    if user is None:
        raise credentials_exception

    return user