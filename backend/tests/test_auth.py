"""Comprehensive authentication test suite.

Tests signup, login, token management, RBAC, and security boundaries.
"""

import time
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole, RefreshToken

client = TestClient(app)

# ── Helpers ──────────────────────────────────────────────────────


def _cleanup_user(email: str):
    """Remove a test user and their refresh tokens by email."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
            db.delete(user)
            db.commit()
    finally:
        db.close()


def _signup(email: str, name: str = "Test User", password: str = "TestPass123!"):
    return client.post(
        "/api/v1/auth/signup",
        json={"name": name, "email": email, "password": password},
    )


def _login(email: str, password: str = "TestPass123!"):
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


def _create_admin(email: str = "admin_test@voyageai.com", password: str = "AdminPass123!"):
    """Directly create an admin user in the database for testing."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                name="Test Admin",
                email=email,
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
                auth_provider="local",
            )
            db.add(user)
            db.commit()
    finally:
        db.close()


# ── 1. Signup Tests ──────────────────────────────────────────────


def test_signup_success():
    email = "signup_success@test.com"
    _cleanup_user(email)
    resp = _signup(email)
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == email
    assert data["role"] == "USER"
    assert data["is_active"] is True
    assert "password_hash" not in data
    _cleanup_user(email)


def test_signup_duplicate_rejected():
    email = "dup_test@test.com"
    _cleanup_user(email)
    _signup(email)
    resp = _signup(email)
    assert resp.status_code == 409
    _cleanup_user(email)


def test_signup_password_is_hashed():
    email = "hash_check@test.com"
    password = "MyPlainPassword1"
    _cleanup_user(email)
    _signup(email, password=password)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        assert user.password_hash != password
        assert user.password_hash.startswith("$2")  # bcrypt prefix
    finally:
        db.close()
    _cleanup_user(email)


# ── 2. Login Tests ───────────────────────────────────────────────


def test_login_success():
    email = "login_ok@test.com"
    _cleanup_user(email)
    _signup(email)
    resp = _login(email)
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    _cleanup_user(email)


def test_login_wrong_password():
    email = "login_bad_pw@test.com"
    _cleanup_user(email)
    _signup(email)
    resp = _login(email, password="WrongPassword!")
    assert resp.status_code == 401
    assert "Invalid email or password" in resp.json()["detail"]
    _cleanup_user(email)


def test_login_nonexistent_user():
    resp = _login("nobody@nowhere.com")
    assert resp.status_code == 401
    assert "Invalid email or password" in resp.json()["detail"]


# ── 3. Protected Endpoint Tests ─────────────────────────────────


def test_me_without_token_rejected():
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)


def test_me_with_valid_token():
    email = "me_test@test.com"
    _cleanup_user(email)
    _signup(email)
    tokens = _login(email).json()
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == email
    assert data["role"] == "USER"
    assert "password_hash" not in data
    _cleanup_user(email)


def test_me_with_invalid_token():
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer totally.invalid.token"},
    )
    assert resp.status_code == 401


def test_me_with_expired_token():
    """Verify expired access tokens are rejected."""
    email = "expired_test@test.com"
    _cleanup_user(email)
    _signup(email)

    # Create an already-expired token
    from app.core.security import create_access_token
    with patch("app.core.security.get_settings") as mock_settings:
        settings = mock_settings.return_value
        settings.JWT_SECRET_KEY = "2b5ead5019373faa35f3f4da7882d94734d4fbe10aa01d4616d4aee4c50d373a"
        settings.JWT_ALGORITHM = "HS256"
        settings.ACCESS_TOKEN_EXPIRE_MINUTES = -1  # already expired

        # We need to get the user id first
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            user_id = user.id
        finally:
            db.close()

        expired_token = create_access_token(user_id, "USER")

    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp.status_code == 401
    _cleanup_user(email)


# ── 4. Refresh Token Tests ──────────────────────────────────────


def test_refresh_token_works():
    email = "refresh_ok@test.com"
    _cleanup_user(email)
    _signup(email)
    tokens = _login(email).json()

    resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    # New tokens should be different (rotation)
    assert new_tokens["refresh_token"] != tokens["refresh_token"]
    _cleanup_user(email)


def test_revoked_refresh_token_rejected():
    email = "revoked_rt@test.com"
    _cleanup_user(email)
    _signup(email)
    tokens = _login(email).json()

    # Use refresh token once (it gets rotated / old one revoked)
    client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    # Try to reuse the old refresh token
    resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert resp.status_code == 401
    _cleanup_user(email)


# ── 5. Logout Tests ─────────────────────────────────────────────


def test_logout_revokes_refresh_token():
    email = "logout_test@test.com"
    _cleanup_user(email)
    _signup(email)
    tokens = _login(email).json()

    # Logout
    resp = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert resp.status_code == 200

    # Old refresh token should no longer work
    resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert resp.status_code == 401
    _cleanup_user(email)


# ── 6. RBAC Tests ────────────────────────────────────────────────


def test_user_cannot_access_admin_endpoint():
    email = "user_rbac@test.com"
    _cleanup_user(email)
    _signup(email)
    tokens = _login(email).json()

    resp = client.get(
        "/api/v1/admin/test",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 403
    _cleanup_user(email)


def test_admin_can_access_admin_endpoint():
    email = "admin_rbac@test.com"
    password = "AdminPass123!"
    _cleanup_user(email)
    _create_admin(email, password)
    tokens = _login(email, password).json()

    resp = client.get(
        "/api/v1/admin/test",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Admin access granted."
    _cleanup_user(email)


def test_public_signup_cannot_create_admin():
    """Verify that sending role=ADMIN in signup body does not work."""
    email = "sneaky_admin@test.com"
    _cleanup_user(email)
    resp = client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Sneaky",
            "email": email,
            "password": "SneakyPass123!",
            "role": "ADMIN",  # This should be ignored
        },
    )
    # Should succeed as a normal USER signup (extra field ignored by Pydantic)
    assert resp.status_code == 201
    assert resp.json()["role"] == "USER"
    _cleanup_user(email)


# ── 7. Inactive User Tests ──────────────────────────────────────


def test_inactive_user_cannot_login():
    email = "inactive@test.com"
    _cleanup_user(email)
    _signup(email)

    # Deactivate user directly in DB
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        user.is_active = False
        db.commit()
    finally:
        db.close()

    resp = _login(email)
    assert resp.status_code == 403
    _cleanup_user(email)


def test_inactive_user_token_rejected():
    email = "inactive_token@test.com"
    _cleanup_user(email)
    _signup(email)
    tokens = _login(email).json()

    # Deactivate user
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        user.is_active = False
        db.commit()
    finally:
        db.close()

    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 403
    _cleanup_user(email)


# ── 8. Validation Tests ─────────────────────────────────────────


def test_signup_short_password_rejected():
    resp = client.post(
        "/api/v1/auth/signup",
        json={"name": "Test", "email": "short@test.com", "password": "abc"},
    )
    assert resp.status_code == 422


def test_signup_invalid_email_rejected():
    resp = client.post(
        "/api/v1/auth/signup",
        json={"name": "Test", "email": "not-an-email", "password": "ValidPass123!"},
    )
    assert resp.status_code == 422


def test_refresh_token_cannot_be_used_as_access():
    """A refresh token should NOT work as a Bearer access token."""
    email = "rt_as_at@test.com"
    _cleanup_user(email)
    _signup(email)
    tokens = _login(email).json()

    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )
    assert resp.status_code == 401
    _cleanup_user(email)
