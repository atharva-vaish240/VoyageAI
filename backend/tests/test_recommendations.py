"""Tests for POST /api/v1/recommendations endpoint."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User, RefreshToken
from app.models.preference import UserPreference
from app.schemas.recommendation import RecommendationsResponse, RecommendationItem
from app.services.ai_service import AIServiceError

client = TestClient(app)


# ── Helpers ────────────────────────────────────────────────────────────

def _cleanup_user(email: str):
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


def _signup_and_login(email: str, name: str = "Rec User", password: str = "Password123!"):
    client.post("/api/v1/auth/signup", json={"name": name, "email": email, "password": password})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()


def _auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _mock_recommendations() -> RecommendationsResponse:
    return RecommendationsResponse(
        seasonal_pick=RecommendationItem(
            category="Seasonal Pick",
            destination="Kyoto, Japan",
            tagline="Autumn leaves & historic temples",
            reason="Peak fall foliage weather with comfortable temperatures.",
            highlights=["Kiyomizu-dera", "Arashiyama Bamboo Grove", "Fushimi Inari"],
        ),
        hidden_gem=RecommendationItem(
            category="Hidden Gem",
            destination="Tirthan Valley, India",
            tagline="Pristine alpine beauty & river streams",
            reason="Peaceful mountain retreat away from tourist crowds.",
            highlights=["Great Himalayan National Park", "Jibhi Waterfalls", "Serolsar Lake"],
        ),
        experience_pick=RecommendationItem(
            category="Experience Pick",
            destination="Rishikesh, India",
            tagline="Ganges rafting & spiritual retreats",
            reason="Ideal blend of high-energy adventure and serene evening rituals.",
            highlights=["White Water Rafting", "Triveni Ghat Aarti", "Beatles Ashram"],
        ),
    )


# ── 1. Unauthenticated request → 401 ──────────────────────────────────

def test_recommendations_unauthenticated_rejected():
    resp = client.post("/api/v1/recommendations")
    assert resp.status_code == 401


# ── 2. Authenticated request returns structured 3 picks ──────────────

@patch("app.api.v1.recommendations.generate_recommendations")
def test_recommendations_authenticated_returns_3_categories(mock_generate):
    email = "rec_success@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)
    mock_generate.return_value = _mock_recommendations()

    resp = client.post("/api/v1/recommendations", headers=_auth_headers(tokens))
    assert resp.status_code == 200
    data = resp.json()

    assert "seasonal_pick" in data
    assert "hidden_gem" in data
    assert "experience_pick" in data

    assert data["seasonal_pick"]["destination"] == "Kyoto, Japan"
    assert data["hidden_gem"]["category"] == "Hidden Gem"
    assert len(data["experience_pick"]["highlights"]) == 3

    _cleanup_user(email)


# ── 3. Passes user preferences to AI service ─────────────────────────

@patch("app.api.v1.recommendations.generate_recommendations")
def test_recommendations_passes_user_preferences(mock_generate):
    email = "rec_prefs@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)
    mock_generate.return_value = _mock_recommendations()

    # Set user preferences
    client.put(
        "/api/v1/preferences",
        json={"food_preference": "vegetarian", "travel_style": "adventure"},
        headers=_auth_headers(tokens),
    )

    resp = client.post("/api/v1/recommendations", headers=_auth_headers(tokens))
    assert resp.status_code == 200

    mock_generate.assert_called_once()
    passed_pref = mock_generate.call_args.kwargs.get("preferences")
    assert passed_pref is not None
    assert passed_pref.food_preference.value == "vegetarian"

    _cleanup_user(email)


# ── 4. AI Service failure returns 503 ─────────────────────────────────

@patch("app.api.v1.recommendations.generate_recommendations")
def test_recommendations_ai_failure_returns_503(mock_generate):
    email = "rec_fail@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)
    mock_generate.side_effect = AIServiceError("GEMINI_API_KEY is not configured.")

    resp = client.post("/api/v1/recommendations", headers=_auth_headers(tokens))
    assert resp.status_code == 503
    assert "GEMINI_API_KEY" in resp.json()["detail"]

    _cleanup_user(email)
