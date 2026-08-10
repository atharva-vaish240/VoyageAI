"""Authentication business logic — signup, login, refresh, logout."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.user import User, RefreshToken, UserRole
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
)


class AuthError(Exception):
    """Raised when an authentication operation fails."""

    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code


# ── Signup ───────────────────────────────────────────────────────


def signup(db: Session, name: str, email: str, password: str) -> User:
    """Create a new user with hashed password. Role is always USER."""
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise AuthError("An account with this email already exists.", status_code=409)

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=UserRole.USER,
        auth_provider="local",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ── Login ────────────────────────────────────────────────────────


def login(db: Session, email: str, password: str) -> dict:
    """Authenticate user and return access + refresh tokens.

    Returns a dict with access_token, refresh_token, and the user object.
    Generic error messages prevent email enumeration.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.password_hash:
        raise AuthError("Invalid email or password.", status_code=401)

    if not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password.", status_code=401)

    if not user.is_active:
        raise AuthError("Account is deactivated.", status_code=403)

    access_token = create_access_token(user.id, user.role.value)
    refresh_token = create_refresh_token(user.id)

    # Persist refresh token hash in the database
    _store_refresh_token(db, user.id, refresh_token)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user,
    }


# ── Refresh ──────────────────────────────────────────────────────


def refresh_tokens(db: Session, refresh_token_str: str) -> dict:
    """Validate a refresh token and issue new access + refresh tokens.

    Implements token rotation: the old refresh token is revoked and a new one
    is issued, limiting the window of compromise if a token is leaked.
    """
    try:
        payload = decode_token(refresh_token_str)
    except Exception:
        raise AuthError("Invalid refresh token.", status_code=401)

    if payload.get("type") != "refresh":
        raise AuthError("Invalid token type.", status_code=401)

    token_hash = hash_token(refresh_token_str)
    stored = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .first()
    )

    if not stored:
        raise AuthError("Invalid refresh token.", status_code=401)

    if stored.revoked:
        raise AuthError("Refresh token has been revoked.", status_code=401)

    if stored.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise AuthError("Refresh token has expired.", status_code=401)

    # Revoke old refresh token (rotation)
    stored.revoked = True
    db.commit()

    user = db.query(User).filter(User.id == stored.user_id).first()
    if not user or not user.is_active:
        raise AuthError("Account not found or deactivated.", status_code=401)

    # Issue new token pair
    new_access = create_access_token(user.id, user.role.value)
    new_refresh = create_refresh_token(user.id)
    _store_refresh_token(db, user.id, new_refresh)

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
    }


# ── Logout ───────────────────────────────────────────────────────


def logout(db: Session, refresh_token_str: str) -> None:
    """Revoke a refresh token. Silently succeeds if already revoked/missing."""
    token_hash = hash_token(refresh_token_str)
    stored = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .first()
    )
    if stored and not stored.revoked:
        stored.revoked = True
        db.commit()


# ── Google OAuth ─────────────────────────────────────────────────


def google_oauth_login(db: Session, google_user_info: dict) -> dict:
    """Handle Google OAuth: find or create user, issue tokens.

    If an account with the same email already exists (e.g. from local signup),
    link it — do not create a duplicate.
    """
    email = google_user_info["email"]
    name = google_user_info.get("name", email.split("@")[0])

    user = db.query(User).filter(User.email == email).first()

    if not user:
        # Create new account via Google
        user = User(
            name=name,
            email=email,
            password_hash=None,
            role=UserRole.USER,
            auth_provider="google",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    if not user.is_active:
        raise AuthError("Account is deactivated.", status_code=403)

    access_token = create_access_token(user.id, user.role.value)
    refresh_token = create_refresh_token(user.id)
    _store_refresh_token(db, user.id, refresh_token)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user,
    }


# ── Internal helpers ─────────────────────────────────────────────


def _store_refresh_token(db: Session, user_id: int, raw_token: str) -> None:
    """Persist a hashed refresh token in the database."""
    from app.core.config import get_settings
    from datetime import timedelta

    settings = get_settings()
    token_record = RefreshToken(
        token_hash=hash_token(raw_token),
        user_id=user_id,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(token_record)
    db.commit()
