"""Tests for POST /api/v1/trips/{trip_id}/generate-itinerary."""

from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User, RefreshToken
from app.models.trip import Trip
from app.models.preference import UserPreference
from app.schemas.itinerary import ItinerarySchema, DaySchema, ActivitySchema
from app.services.ai_service import AIServiceError

client = TestClient(app)


# ── Helpers ────────────────────────────────────────────────────────────

def _cleanup_user(email: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.query(UserPreference).filter(UserPreference.user_id == user.id).delete()
            db.query(Trip).filter(Trip.user_id == user.id).delete()
            db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
            db.delete(user)
            db.commit()
    finally:
        db.close()


def _signup_and_login(email: str, name: str = "Test User", password: str = "TestPass123!"):
    client.post("/api/v1/auth/signup", json={"name": name, "email": email, "password": password})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()


def _auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _create_trip(tokens: dict, destination: str = "Tokyo") -> int:
    start = date.today()
    end = start + timedelta(days=3)
    resp = client.post(
        "/api/v1/trips",
        json={
            "title": "Test Trip",
            "destination": destination,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "status": "PLANNED",
        },
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 201, resp.json()
    return resp.json()["id"]


def _mock_itinerary() -> ItinerarySchema:
    return ItinerarySchema(
        trip_summary="A wonderful trip to Tokyo.",
        days=[
            DaySchema(
                date=date.today(),
                activities=[
                    ActivitySchema(
                        title="Shibuya Crossing",
                        description="Visit the iconic crossing.",
                        approximate_time="10:00 AM",
                        location="Shibuya, Tokyo",
                    )
                ],
            )
        ],
    )


# ── A. Unauthenticated → 401 ───────────────────────────────────────────

def test_generate_itinerary_unauthenticated():
    resp = client.post("/api/v1/trips/999/generate-itinerary")
    assert resp.status_code == 401


# ── B. Authenticated user can generate itinerary for their trip ────────

@patch("app.api.v1.trips.generate_itinerary")
def test_generate_itinerary_success(mock_generate):
    email = "gen_itinerary_ok@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)
    trip_id = _create_trip(tokens)
    mock_generate.return_value = _mock_itinerary()

    resp = client.post(
        f"/api/v1/trips/{trip_id}/generate-itinerary",
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "trip_summary" in data
    assert "days" in data
    assert isinstance(data["days"], list)

    _cleanup_user(email)


# ── C. Cross-user access → 404 ─────────────────────────────────────────

@patch("app.api.v1.trips.generate_itinerary")
def test_generate_itinerary_other_users_trip_returns_404(mock_generate):
    owner_email = "gen_owner@test.com"
    attacker_email = "gen_attacker@test.com"
    _cleanup_user(owner_email)
    _cleanup_user(attacker_email)

    owner_tokens = _signup_and_login(owner_email)
    attacker_tokens = _signup_and_login(attacker_email)
    trip_id = _create_trip(owner_tokens)

    resp = client.post(
        f"/api/v1/trips/{trip_id}/generate-itinerary",
        headers=_auth_headers(attacker_tokens),
    )
    assert resp.status_code == 404
    mock_generate.assert_not_called()

    _cleanup_user(owner_email)
    _cleanup_user(attacker_email)


# ── D. AI service is called with correct trip + preference info ─────────

@patch("app.api.v1.trips.generate_itinerary")
def test_generate_itinerary_passes_correct_context(mock_generate):
    email = "gen_ctx@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)
    trip_id = _create_trip(tokens, destination="Barcelona")
    mock_generate.return_value = _mock_itinerary()

    # Set preferences for the user
    client.put(
        "/api/v1/preferences",
        json={"food_preference": "vegan", "travel_style": "cultural"},
        headers=_auth_headers(tokens),
    )

    resp = client.post(
        f"/api/v1/trips/{trip_id}/generate-itinerary",
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 200

    # Verify service was called with destination and a preferences object
    mock_generate.assert_called_once()
    call_kwargs = mock_generate.call_args.kwargs
    assert call_kwargs["destination"] == "Barcelona"
    assert call_kwargs["preferences"] is not None  # preferences were loaded

    _cleanup_user(email)


# ── E. AI service failure → clean 503 error ─────────────────────────────

@patch("app.api.v1.trips.generate_itinerary")
def test_generate_itinerary_ai_failure_returns_503(mock_generate):
    email = "gen_fail@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)
    trip_id = _create_trip(tokens)
    mock_generate.side_effect = AIServiceError("GEMINI_API_KEY is not configured.")

    resp = client.post(
        f"/api/v1/trips/{trip_id}/generate-itinerary",
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 503
    assert "GEMINI_API_KEY" in resp.json()["detail"]

    _cleanup_user(email)


# ── F. Response conforms to ItinerarySchema ─────────────────────────────

@patch("app.api.v1.trips.generate_itinerary")
def test_generate_itinerary_response_schema(mock_generate):
    email = "gen_schema@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)
    trip_id = _create_trip(tokens)
    mock_generate.return_value = _mock_itinerary()

    resp = client.post(
        f"/api/v1/trips/{trip_id}/generate-itinerary",
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 200
    data = resp.json()

    # Validate full schema shape
    parsed = ItinerarySchema.model_validate(data)
    assert len(parsed.days) >= 1
    assert len(parsed.days[0].activities) >= 1
    assert parsed.days[0].activities[0].title == "Shibuya Crossing"

    _cleanup_user(email)


# ── G. Missing destination → 400 ────────────────────────────────────────

@patch("app.api.v1.trips.generate_itinerary")
def test_generate_itinerary_missing_destination_returns_400(mock_generate):
    email = "gen_nodest@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)

    # Create a trip WITHOUT a destination
    start = date.today()
    end = start + timedelta(days=3)
    resp = client.post(
        "/api/v1/trips",
        json={
            "title": "No Destination Trip",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "status": "DRAFT",
        },
        headers=_auth_headers(tokens),
    )
    trip_id = resp.json()["id"]

    resp = client.post(
        f"/api/v1/trips/{trip_id}/generate-itinerary",
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 400
    assert "destination" in resp.json()["detail"].lower()
    mock_generate.assert_not_called()

    _cleanup_user(email)
