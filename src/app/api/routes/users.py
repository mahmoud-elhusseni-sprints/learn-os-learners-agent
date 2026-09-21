from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.app.api.dependencies.auth import get_current_user
from src.app.database.connection import get_db
from src.app.models.user import User
from src.app.schemas.user import UserResponse
from src.app.services import user_service

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user = user_service.get_user_by_id(db, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user