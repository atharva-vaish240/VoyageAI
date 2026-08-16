"""Tests for GET and PUT /api/v1/trips/{trip_id}/itinerary endpoints,

verifying authentication, authorization, validation, PostgreSQL persistence,
and Redis cache isolation.
"""

import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.preference import UserPreference
from app.models.trip import Trip
from app.models.user import RefreshToken, User
from app.schemas.itinerary import ActivitySchema, DaySchema, ItinerarySchema
from app.services.ai_service import (
    compute_itinerary_cache_key,
    generate_itinerary,
)

client = TestClient(app)


# ── In-Memory Fake Redis Helper ────────────────────────────────────────

class InMemoryRedis:
    """Lightweight in-memory Redis mock for testing cache isolation."""

    def __init__(self):
        self.store = {}
        self.ttls = {}

    def get(self, key: str):
        return self.store.get(key)

    def set(self, key: str, value: str):
        self.store[key] = value

    def setex(self, key: str, time: int, value: str):
        self.store[key] = value
        self.ttls[key] = time

    def delete(self, *keys):
        for k in keys:
            self.store.pop(k, None)
            self.ttls.pop(k, None)


# ── Fixtures & Helpers ─────────────────────────────────────────────────

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


def _signup_and_login(email: str, name: str = "Itinerary User", password: str = "TestPass123!"):
    client.post("/api/v1/auth/signup", json={"name": name, "email": email, "password": password})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()


def _auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _create_trip(tokens: dict, destination: str = "Goa", start_days_ahead: int = 5, duration: int = 3) -> int:
    start = date.today() + timedelta(days=start_days_ahead)
    end = start + timedelta(days=duration)
    resp = client.post(
        "/api/v1/trips",
        json={
            "title": f"Trip to {destination}",
            "destination": destination,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "status": "PLANNED",
            "num_travellers": 2,
            "budget": "₹ 30000",
            "special_requirements": "Beachfront preferred",
        },
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 201, resp.json()
    return resp.json()["id"]


def _sample_itinerary_payload(summary: str = "Original AI Generated Itinerary") -> dict:
    today = date.today()
    return {
        "trip_summary": summary,
        "days": [
            {
                "date": today.isoformat(),
                "activities": [
                    {
                        "title": "Calangute Beach Walk",
                        "description": "Morning stroll along the shoreline.",
                        "approximate_time": "08:00 AM",
                        "location": "Calangute Beach, Goa",
                    },
                    {
                        "title": "Seafood Lunch",
                        "description": "Enjoy local Goan fish curry.",
                        "approximate_time": "01:00 PM",
                        "location": "Britto's, Baga",
                    },
                ],
            },
            {
                "date": (today + timedelta(days=1)).isoformat(),
                "activities": [
                    {
                        "title": "Fort Aguada Visit",
                        "description": "Explore the 17th-century Portuguese lighthouse and fort.",
                        "approximate_time": "10:00 AM",
                        "location": "Sinquerim, Goa",
                    }
                ],
            },
        ],
    }


# ── 1. Unauthenticated & Ownership Tests ──────────────────────────────

def test_get_itinerary_unauthenticated():
    """GET /api/v1/trips/{trip_id}/itinerary without token returns 401."""
    resp = client.get("/api/v1/trips/999/itinerary")
    assert resp.status_code == 401


def test_put_itinerary_unauthenticated():
    """PUT /api/v1/trips/{trip_id}/itinerary without token returns 401."""
    resp = client.put("/api/v1/trips/999/itinerary", json=_sample_itinerary_payload())
    assert resp.status_code == 401


def test_get_itinerary_not_found_or_not_owner():
    """GET /api/v1/trips/{trip_id}/itinerary for another user's trip returns 404."""
    user_a = "itinerary_owner_a@test.com"
    user_b = "itinerary_owner_b@test.com"
    _cleanup_user(user_a)
    _cleanup_user(user_b)

    try:
        tokens_a = _signup_and_login(user_a, name="User A")
        tokens_b = _signup_and_login(user_b, name="User B")

        trip_a_id = _create_trip(tokens_a, destination="Goa")

        # User B attempts to access User A's itinerary
        resp = client.get(f"/api/v1/trips/{trip_a_id}/itinerary", headers=_auth_headers(tokens_b))
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Trip not found."
    finally:
        _cleanup_user(user_a)
        _cleanup_user(user_b)


def test_put_itinerary_not_owner():
    """PUT /api/v1/trips/{trip_id}/itinerary for another user's trip returns 404."""
    user_a = "itinerary_owner_a2@test.com"
    user_b = "itinerary_owner_b2@test.com"
    _cleanup_user(user_a)
    _cleanup_user(user_b)

    try:
        tokens_a = _signup_and_login(user_a, name="User A")
        tokens_b = _signup_and_login(user_b, name="User B")

        trip_a_id = _create_trip(tokens_a, destination="Goa")

        # User B attempts to modify User A's trip itinerary
        resp = client.put(
            f"/api/v1/trips/{trip_a_id}/itinerary",
            json=_sample_itinerary_payload("Hacked Itinerary"),
            headers=_auth_headers(tokens_b),
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Trip not found."
    finally:
        _cleanup_user(user_a)
        _cleanup_user(user_b)


# ── 2. Missing Itinerary Returns 404 ───────────────────────────────────

def test_get_missing_itinerary_returns_404():
    """GET /api/v1/trips/{trip_id}/itinerary when trip has no itinerary returns 404."""
    user = "itinerary_missing@test.com"
    _cleanup_user(user)

    try:
        tokens = _signup_and_login(user)
        trip_id = _create_trip(tokens)

        resp = client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=_auth_headers(tokens))
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Itinerary not found for this trip."
    finally:
        _cleanup_user(user)


# ── 3. PUT and GET Itinerary for Authenticated Owner ───────────────────

def test_put_and_get_itinerary_authenticated_owner():
    """PUT saves the itinerary and GET retrieves the updated itinerary for the owner."""
    user = "itinerary_crud_owner@test.com"
    _cleanup_user(user)

    try:
        tokens = _signup_and_login(user)
        trip_id = _create_trip(tokens)

        payload = _sample_itinerary_payload("My Custom Hand-crafted Itinerary")

        # 1. PUT the itinerary
        put_resp = client.put(
            f"/api/v1/trips/{trip_id}/itinerary",
            json=payload,
            headers=_auth_headers(tokens),
        )
        assert put_resp.status_code == 200
        saved_data = put_resp.json()
        assert saved_data["trip_summary"] == "My Custom Hand-crafted Itinerary"
        assert len(saved_data["days"]) == 2
        assert len(saved_data["days"][0]["activities"]) == 2

        # 2. GET the itinerary
        get_resp = client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=_auth_headers(tokens))
        assert get_resp.status_code == 200
        retrieved_data = get_resp.json()
        assert retrieved_data["trip_summary"] == "My Custom Hand-crafted Itinerary"
        assert retrieved_data["days"][0]["activities"][0]["title"] == "Calangute Beach Walk"

        # 3. Direct DB verification
        db = SessionLocal()
        try:
            db_trip = db.query(Trip).filter(Trip.id == trip_id).first()
            assert db_trip is not None
            assert db_trip.itinerary["trip_summary"] == "My Custom Hand-crafted Itinerary"
            assert len(db_trip.itinerary["days"]) == 2
        finally:
            db.close()
    finally:
        _cleanup_user(user)


# ── 4. Validation Rejection (422) for Malformed Data ───────────────────

def test_put_invalid_itinerary_structure():
    """PUT /api/v1/trips/{trip_id}/itinerary with malformed structure returns 422."""
    user = "itinerary_validation@test.com"
    _cleanup_user(user)

    try:
        tokens = _signup_and_login(user)
        trip_id = _create_trip(tokens)

        # Missing 'days'
        resp1 = client.put(
            f"/api/v1/trips/{trip_id}/itinerary",
            json={"trip_summary": "Only summary"},
            headers=_auth_headers(tokens),
        )
        assert resp1.status_code == 422

        # Invalid date format in day
        bad_payload = {
            "trip_summary": "Invalid Date",
            "days": [
                {
                    "date": "not-a-date",
                    "activities": [],
                }
            ],
        }
        resp2 = client.put(
            f"/api/v1/trips/{trip_id}/itinerary",
            json=bad_payload,
            headers=_auth_headers(tokens),
        )
        assert resp2.status_code == 422

        # Missing activity required field (e.g. title or approximate_time)
        bad_activity_payload = {
            "trip_summary": "Missing title",
            "days": [
                {
                    "date": date.today().isoformat(),
                    "activities": [
                        {
                            "description": "No title here",
                            "approximate_time": "10:00 AM",
                        }
                    ],
                }
            ],
        }
        resp3 = client.put(
            f"/api/v1/trips/{trip_id}/itinerary",
            json=bad_activity_payload,
            headers=_auth_headers(tokens),
        )
        assert resp3.status_code == 422
    finally:
        _cleanup_user(user)


# ── 5. Redis Isolation & Cross-User Independence ───────────────────────

@patch("google.generativeai.GenerativeModel")
@patch("app.services.ai_service.get_redis_client")
def test_redis_isolation_and_cross_user_independent_editing(mock_get_redis, mock_gen_model_class):
    """
    Scenario:
    1. User A generates an itinerary for Goa -> Miss -> Gemini called -> stored in Redis cache.
    2. User B requests same itinerary for Goa -> Hit -> gets Redis cached itinerary -> stored in DB for User B.
    3. User A edits their itinerary (e.g. changes summary, modifies activity).
    4. Verify:
       - User A's DB copy has the edits.
       - Redis cache still has the UNMODIFIED original itinerary.
       - User B's DB copy and GET endpoint still have the UNMODIFIED original itinerary.
    """
    fake_redis = InMemoryRedis()
    mock_get_redis.return_value = fake_redis

    initial_sample = ItinerarySchema(
        trip_summary="Shared Original Goa Itinerary from Gemini",
        days=[
            DaySchema(
                date=date(2026, 11, 1),
                activities=[
                    ActivitySchema(
                        title="Original AI Beach Walk",
                        description="Walk on Anjuna Beach.",
                        approximate_time="09:00 AM",
                        location="Anjuna",
                    )
                ],
            )
        ],
    )

    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = initial_sample.model_dump_json()
    mock_model.generate_content.return_value = mock_response
    mock_gen_model_class.return_value = mock_model

    user_a_email = "user_a_isolation@test.com"
    user_b_email = "user_b_isolation@test.com"
    _cleanup_user(user_a_email)
    _cleanup_user(user_b_email)

    try:
        tokens_a = _signup_and_login(user_a_email, name="User A")
        tokens_b = _signup_and_login(user_b_email, name="User B")

        # Set matching preferences
        pref = {"food_preference": "vegetarian", "travel_style": "relaxed"}
        client.put("/api/v1/preferences", json=pref, headers=_auth_headers(tokens_a))
        client.put("/api/v1/preferences", json=pref, headers=_auth_headers(tokens_b))

        start = date(2026, 11, 1)
        end = date(2026, 11, 3)

        trip_body = {
            "title": "Goa Trip",
            "destination": "Goa",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "num_travellers": 2,
            "budget": "₹ 25000",
            "special_requirements": "None",
        }

        trip_a_resp = client.post("/api/v1/trips", json=trip_body, headers=_auth_headers(tokens_a))
        trip_b_resp = client.post("/api/v1/trips", json=trip_body, headers=_auth_headers(tokens_b))
        trip_a_id = trip_a_resp.json()["id"]
        trip_b_id = trip_b_resp.json()["id"]

        # Step 1: User A generates itinerary (Cache Miss -> Gemini -> Redis cached)
        gen_a_resp = client.post(f"/api/v1/trips/{trip_a_id}/generate-itinerary", headers=_auth_headers(tokens_a))
        assert gen_a_resp.status_code == 200
        assert gen_a_resp.json()["trip_summary"] == "Shared Original Goa Itinerary from Gemini"
        assert mock_model.generate_content.call_count == 1

        # Check key in fake_redis
        assert len(fake_redis.store) == 1
        cache_key = list(fake_redis.store.keys())[0]
        assert cache_key.startswith("itinerary:")
        redis_content_before = json.loads(fake_redis.store[cache_key])
        assert redis_content_before["trip_summary"] == "Shared Original Goa Itinerary from Gemini"

        # Step 2: User B generates equivalent itinerary (Cache Hit -> Redis -> DB saved)
        gen_b_resp = client.post(f"/api/v1/trips/{trip_b_id}/generate-itinerary", headers=_auth_headers(tokens_b))
        assert gen_b_resp.status_code == 200
        assert gen_b_resp.json()["trip_summary"] == "Shared Original Goa Itinerary from Gemini"
        # Gemini was NOT called again
        assert mock_model.generate_content.call_count == 1

        # Step 3: User A modifies their itinerary via PUT
        user_a_modified_payload = {
            "trip_summary": "User A's Custom Private Edits",
            "days": [
                {
                    "date": "2026-11-01",
                    "activities": [
                        {
                            "title": "Private Scuba Diving Session",
                            "description": "Personalized diving in Grand Island.",
                            "approximate_time": "07:30 AM",
                            "location": "Grand Island, Goa",
                        },
                        {
                            "title": "Exclusive Sunset Dinner",
                            "description": "Candlelight private dinner on the cliff.",
                            "approximate_time": "07:00 PM",
                            "location": "Thalassa, Siolim",
                        },
                    ],
                }
            ],
        }
        put_a_resp = client.put(
            f"/api/v1/trips/{trip_a_id}/itinerary",
            json=user_a_modified_payload,
            headers=_auth_headers(tokens_a),
        )
        assert put_a_resp.status_code == 200
        assert put_a_resp.json()["trip_summary"] == "User A's Custom Private Edits"

        # Step 4: Verify Redis Cache was NOT changed
        redis_content_after = json.loads(fake_redis.store[cache_key])
        assert redis_content_after["trip_summary"] == "Shared Original Goa Itinerary from Gemini"
        assert redis_content_after["days"][0]["activities"][0]["title"] == "Original AI Beach Walk"
        assert "User A's Custom Private Edits" not in fake_redis.store[cache_key]

        # Step 5: Verify User B's itinerary remains UNTOUCHED
        get_b_resp = client.get(f"/api/v1/trips/{trip_b_id}/itinerary", headers=_auth_headers(tokens_b))
        assert get_b_resp.status_code == 200
        b_data = get_b_resp.json()
        assert b_data["trip_summary"] == "Shared Original Goa Itinerary from Gemini"
        assert b_data["days"][0]["activities"][0]["title"] == "Original AI Beach Walk"
        assert len(b_data["days"][0]["activities"]) == 1

        # Step 6: Verify User A's itinerary has their new edits
        get_a_resp = client.get(f"/api/v1/trips/{trip_a_id}/itinerary", headers=_auth_headers(tokens_a))
        assert get_a_resp.status_code == 200
        a_data = get_a_resp.json()
        assert a_data["trip_summary"] == "User A's Custom Private Edits"
        assert a_data["days"][0]["activities"][0]["title"] == "Private Scuba Diving Session"
        assert len(a_data["days"][0]["activities"]) == 2

    finally:
        _cleanup_user(user_a_email)
        _cleanup_user(user_b_email)
