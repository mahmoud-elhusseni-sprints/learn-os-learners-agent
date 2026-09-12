from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.app.schemas.auth import SigninRequest, SignupRequest, TokenResponse

from src.app.database.connection import get_db
from src.app.schemas.auth import SignupRequest
from src.app.schemas.user import UserResponse
from src.app.services import user_service


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def signup(
    signup_data: SignupRequest,
    db: Session = Depends(get_db),
):
    try:
        return user_service.signup(db, signup_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post(
    "/signin",
    response_model=TokenResponse,
)
def signin(
    signin_data: SigninRequest,
    db: Session = Depends(get_db),
):
    try:
        access_token = user_service.signin(
            db,
            signin_data.email,
            signin_data.password,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
    )