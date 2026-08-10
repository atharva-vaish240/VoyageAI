"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import (
    SignupRequest,
    LoginRequest,
    RefreshRequest,
    UserResponse,
    TokenResponse,
    MessageResponse,
)
from app.services.auth_service import AuthError, signup, login, refresh_tokens, logout

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=UserResponse, status_code=201)
def signup_route(body: SignupRequest, db: Session = Depends(get_db)):
    """Register a new user. Role is always USER — cannot be overridden."""
    try:
        user = signup(db, name=body.name, email=body.email, password=body.password)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return user


@router.post("/login", response_model=TokenResponse)
def login_route(body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email and password. Returns access + refresh tokens."""
    try:
        result = login(db, email=body.email, password=body.password)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_route(body: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    try:
        result = refresh_tokens(db, body.refresh_token)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
    )


@router.post("/logout", response_model=MessageResponse)
def logout_route(body: RefreshRequest, db: Session = Depends(get_db)):
    """Revoke a refresh token. Idempotent — always returns success."""
    logout(db, body.refresh_token)
    return MessageResponse(message="Logged out successfully.")


@router.get("/me", response_model=UserResponse)
def me_route(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user
