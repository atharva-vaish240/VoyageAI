"""Tests for the User Preferences API endpoints."""

from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User, RefreshToken
from app.models.preference import UserPreference

client = TestClient(app)


def _cleanup_user(email: str):
    """Remove a test user and their refresh tokens + preferences by email."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.query(UserPreference).filter(UserPreference.user_id == user.id).delete()
            db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
            db.delete(user)
            db.commit()
    finally:
        db.close()


def _signup_and_login(email: str, name: str = "Test User", password: str = "TestPass123!"):
    client.post(
        "/api/v1/auth/signup",
        json={"name": name, "email": email, "password": password},
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return resp.json()


# ── 1. Unauthenticated Request Rejected ────────────────────────────────

def test_get_preferences_unauthenticated_rejected():
    resp = client.get("/api/v1/preferences")
    assert resp.status_code == 401


def test_put_preferences_unauthenticated_rejected():
    resp = client.put(
        "/api/v1/preferences",
        json={"food_preference": "vegetarian"},
    )
    assert resp.status_code == 401


# ── 2. Authenticated GET (Defaults Auto-Created) ──────────────────────

def test_get_preferences_authenticated_defaults():
    email = "pref_defaults@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)

    resp = client.get(
        "/api/v1/preferences",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["food_preference"] == "no_preference"
    assert data["drinking_preference"] == "no_preference"
    assert data["travel_style"] == "mixed"
    assert data["travel_pace"] == "moderate"
    assert data["accommodation_preference"] == "no_preference"
    assert data["interests"] == []
    assert data["additional_preferences"] is None

    _cleanup_user(email)


# ── 3. Create / Put Preferences ──────────────────────────────────────

def test_create_and_update_preferences():
    email = "pref_update@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)

    # First update (creates)
    payload = {
        "food_preference": "vegan",
        "drinking_preference": "non_drinker",
        "travel_style": "adventure",
        "travel_pace": "packed",
        "accommodation_preference": "hostel",
        "interests": ["mountains", "nature"],
        "additional_preferences": "Prefer train travel if possible.",
    }
    resp = client.put(
        "/api/v1/preferences",
        json=payload,
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["food_preference"] == "vegan"
    assert data["drinking_preference"] == "non_drinker"
    assert data["travel_style"] == "adventure"
    assert data["travel_pace"] == "packed"
    assert data["accommodation_preference"] == "hostel"
    assert data["interests"] == ["mountains", "nature"]
    assert data["additional_preferences"] == "Prefer train travel if possible."

    # Verify subsequent GET returns the updated values
    get_resp = client.get(
        "/api/v1/preferences",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["food_preference"] == "vegan"

    _cleanup_user(email)


# ── 4. Preferences Belong to Correct User & Isolated ──────────────────

def test_preferences_isolation():
    email_a = "user_a@test.com"
    email_b = "user_b@test.com"
    _cleanup_user(email_a)
    _cleanup_user(email_b)

    tokens_a = _signup_and_login(email_a)
    tokens_b = _signup_and_login(email_b)

    # User A sets preferences to vegan/drinker
    client.put(
        "/api/v1/preferences",
        json={
            "food_preference": "vegan",
            "drinking_preference": "drinker",
            "travel_style": "relaxed",
            "travel_pace": "relaxed",
            "accommodation_preference": "resort",
            "interests": ["beaches"],
        },
        headers={"Authorization": f"Bearer {tokens_a['access_token']}"},
    )

    # User B gets their own preferences (should be defaults)
    resp_b = client.get(
        "/api/v1/preferences",
        headers={"Authorization": f"Bearer {tokens_b['access_token']}"},
    )
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert data_b["food_preference"] == "no_preference"
    assert data_b["drinking_preference"] == "no_preference"

    # User B updates their preferences to vegetarian/non_drinker
    client.put(
        "/api/v1/preferences",
        json={
            "food_preference": "vegetarian",
            "drinking_preference": "non_drinker",
            "travel_style": "cultural",
            "travel_pace": "moderate",
            "accommodation_preference": "hotel",
            "interests": ["history"],
        },
        headers={"Authorization": f"Bearer {tokens_b['access_token']}"},
    )

    # User A gets their preferences (should still be vegan/drinker)
    resp_a = client.get(
        "/api/v1/preferences",
        headers={"Authorization": f"Bearer {tokens_a['access_token']}"},
    )
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert data_a["food_preference"] == "vegan"
    assert data_a["drinking_preference"] == "drinker"

    _cleanup_user(email_a)
    _cleanup_user(email_b)


# ── 5. Validation Rejects Bad Input ───────────────────────────────────

def test_preferences_invalid_enum_rejected():
    email = "invalid_enum@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)

    resp = client.put(
        "/api/v1/preferences",
        json={
            "food_preference": "invalid_food_type",
            "drinking_preference": "non_drinker",
        },
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 422

    _cleanup_user(email)
