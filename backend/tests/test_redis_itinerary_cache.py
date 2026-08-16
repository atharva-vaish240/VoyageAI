"""Focused tests for Redis caching in the AI itinerary generation flow."""

import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
import redis
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.main import app
from app.models.preference import (
    AccommodationPreference,
    DrinkingPreference,
    FoodPreference,
    TravelPace,
    TravelStyle,
    UserPreference,
)
from app.models.trip import Trip
from app.models.user import RefreshToken, User
from app.schemas.itinerary import ActivitySchema, DaySchema, ItinerarySchema
from app.services.ai_service import (
    AIServiceError,
    compute_itinerary_cache_key,
    generate_itinerary,
    get_cached_itinerary,
    set_cached_itinerary,
)

client = TestClient(app)


# ── In-Memory Fake Redis Helper ────────────────────────────────────────

class InMemoryRedis:
    """Lightweight in-memory Redis mock for fast, isolated testing."""

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

    def flushall(self):
        self.store.clear()
        self.ttls.clear()


def _sample_itinerary(summary: str = "A wonderful Tokyo trip.") -> ItinerarySchema:
    return ItinerarySchema(
        trip_summary=summary,
        days=[
            DaySchema(
                date=date(2026, 10, 1),
                activities=[
                    ActivitySchema(
                        title="Shibuya Crossing",
                        description="Explore Shibuya.",
                        approximate_time="09:00 AM",
                        location="Shibuya",
                    )
                ],
            )
        ],
    )


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


# ── 1. Deterministic Cache Key Tests ──────────────────────────────────

def test_cache_key_deterministic_and_no_user_id():
    """Identical inputs produce the exact same key, and user_id is NOT included."""
    pref1 = UserPreference(
        user_id=101,  # User 1
        food_preference=FoodPreference.VEGAN,
        travel_style=TravelStyle.CULTURAL,
        travel_pace=TravelPace.MODERATE,
        interests="temples, museums",
    )
    pref2 = UserPreference(
        user_id=202,  # User 2 (different user_id!)
        food_preference=FoodPreference.VEGAN,
        travel_style=TravelStyle.CULTURAL,
        travel_pace=TravelPace.MODERATE,
        interests="temples, museums",
    )

    key1 = compute_itinerary_cache_key(
        destination="Tokyo",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 5),
        preferences=pref1,
        num_travellers=2,
        budget="50000",
        special_requirements="None",
    )

    key2 = compute_itinerary_cache_key(
        destination="Tokyo",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 5),
        preferences=pref2,
        num_travellers=2,
        budget="50000",
        special_requirements="None",
    )

    assert key1 == key2
    assert key1.startswith("itinerary:")
    assert "101" not in key1
    assert "202" not in key1


def test_cache_key_normalization():
    """Whitespace, casing, interest order, and 'no_preference' normalize to identical keys."""
    pref_a = UserPreference(
        food_preference=FoodPreference.NO_PREFERENCE,
        interests="museums, temples, art",
        additional_preferences="  Near Metro  ",
    )
    pref_b = UserPreference(
        food_preference=None,
        interests="  art ,  museums,temples  ",
        additional_preferences="near metro",
    )

    key_a = compute_itinerary_cache_key(
        destination="  Tokyo  ",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 5),
        preferences=pref_a,
    )
    key_b = compute_itinerary_cache_key(
        destination="tokyo",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 5),
        preferences=pref_b,
    )

    assert key_a == key_b


def test_cache_key_different_inputs_produce_different_keys():
    """Different destinations, dates, preferences, or planning details produce different keys."""
    base_dest = "Tokyo"
    base_start = date(2026, 10, 1)
    base_end = date(2026, 10, 5)

    key_base = compute_itinerary_cache_key(base_dest, base_start, base_end)

    # Different destination
    key_dest = compute_itinerary_cache_key("Kyoto", base_start, base_end)
    assert key_dest != key_base

    # Different dates
    key_dates = compute_itinerary_cache_key(base_dest, base_start, date(2026, 10, 8))
    assert key_dates != key_base

    # Different preferences
    pref_vegan = UserPreference(food_preference=FoodPreference.VEGAN)
    pref_non_veg = UserPreference(food_preference=FoodPreference.NON_VEGETARIAN)
    key_pref1 = compute_itinerary_cache_key(base_dest, base_start, base_end, preferences=pref_vegan)
    key_pref2 = compute_itinerary_cache_key(base_dest, base_start, base_end, preferences=pref_non_veg)
    assert key_pref1 != key_base
    assert key_pref1 != key_pref2

    # Different budget / travellers
    key_travellers = compute_itinerary_cache_key(base_dest, base_start, base_end, num_travellers=4)
    assert key_travellers != key_base


# ── 2. Cache Miss Calls Gemini & Stores in Redis ──────────────────────

@patch("google.generativeai.GenerativeModel")
@patch("app.services.ai_service.get_redis_client")
def test_cache_miss_calls_gemini_and_stores_in_redis(mock_get_redis, mock_gen_model_class):
    fake_redis = InMemoryRedis()
    mock_get_redis.return_value = fake_redis

    mock_model = MagicMock()
    mock_response = MagicMock()
    sample = _sample_itinerary()
    mock_response.text = sample.model_dump_json()
    mock_model.generate_content.return_value = mock_response
    mock_gen_model_class.return_value = mock_model

    start = date(2026, 10, 1)
    end = date(2026, 10, 1)

    result = generate_itinerary(destination="Tokyo", start_date=start, end_date=end)

    # Gemini was called
    mock_model.generate_content.assert_called_once()
    assert result.trip_summary == sample.trip_summary

    # Result was saved in Redis
    key = compute_itinerary_cache_key("Tokyo", start, end)
    assert key in fake_redis.store
    stored_json = json.loads(fake_redis.store[key])
    assert stored_json["trip_summary"] == sample.trip_summary
    # Check TTL is set
    assert fake_redis.ttls.get(key) == get_settings().REDIS_CACHE_TTL


# ── 3. Cache Hit Does Not Call Gemini ──────────────────────────────────

@patch("google.generativeai.GenerativeModel")
@patch("app.services.ai_service.get_redis_client")
def test_cache_hit_does_not_call_gemini(mock_get_redis, mock_gen_model_class):
    fake_redis = InMemoryRedis()
    mock_get_redis.return_value = fake_redis

    start = date(2026, 10, 1)
    end = date(2026, 10, 1)
    key = compute_itinerary_cache_key("Tokyo", start, end)

    # Pre-populate Redis with cached itinerary
    cached_obj = _sample_itinerary("Cached Tokyo Trip")
    fake_redis.setex(key, 3600, cached_obj.model_dump_json())

    result = generate_itinerary(destination="Tokyo", start_date=start, end_date=end)

    # Gemini model is never instantiated or called
    mock_gen_model_class.assert_not_called()
    assert result.trip_summary == "Cached Tokyo Trip"


# ── 4. Cross-User Cache Reuse (Integration Test) ───────────────────────

@patch("google.generativeai.GenerativeModel")
@patch("app.services.ai_service.get_redis_client")
def test_cross_user_cache_reuse_endpoint(mock_get_redis, mock_gen_model_class):
    """User 1 generates an itinerary (miss -> Gemini -> stored in Redis).
    User 2 generates equivalent itinerary (hit -> Redis -> Gemini not called)."""
    fake_redis = InMemoryRedis()
    mock_get_redis.return_value = fake_redis

    mock_model = MagicMock()
    mock_response = MagicMock()
    sample = _sample_itinerary("Shared Itinerary for Tokyo")
    mock_response.text = sample.model_dump_json()
    mock_model.generate_content.return_value = mock_response
    mock_gen_model_class.return_value = mock_model

    user1_email = "user1_cache@test.com"
    user2_email = "user2_cache@test.com"
    _cleanup_user(user1_email)
    _cleanup_user(user2_email)

    try:
        user1_tokens = _signup_and_login(user1_email, name="User One")
        user2_tokens = _signup_and_login(user2_email, name="User Two")

        start = date(2026, 11, 10)
        end = date(2026, 11, 12)

        # Set same preferences for both users
        pref_payload = {"food_preference": "vegan", "travel_style": "relaxed"}
        client.put("/api/v1/preferences", json=pref_payload, headers=_auth_headers(user1_tokens))
        client.put("/api/v1/preferences", json=pref_payload, headers=_auth_headers(user2_tokens))

        # Create identical trip specs for User 1 and User 2
        trip_body = {
            "title": "Tokyo Trip",
            "destination": "Tokyo",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "num_travellers": 2,
            "budget": "₹ 40000",
            "special_requirements": "None",
        }
        trip1_resp = client.post("/api/v1/trips", json=trip_body, headers=_auth_headers(user1_tokens))
        trip2_resp = client.post("/api/v1/trips", json=trip_body, headers=_auth_headers(user2_tokens))
        trip1_id = trip1_resp.json()["id"]
        trip2_id = trip2_resp.json()["id"]

        # 1. User 1 calls generate-itinerary -> Cache Miss -> Gemini called
        gen1_resp = client.post(
            f"/api/v1/trips/{trip1_id}/generate-itinerary",
            headers=_auth_headers(user1_tokens),
        )
        assert gen1_resp.status_code == 200
        assert gen1_resp.json()["trip_summary"] == "Shared Itinerary for Tokyo"
        assert mock_model.generate_content.call_count == 1

        # 2. User 2 calls generate-itinerary -> Cache Hit -> Gemini NOT called again
        gen2_resp = client.post(
            f"/api/v1/trips/{trip2_id}/generate-itinerary",
            headers=_auth_headers(user2_tokens),
        )
        assert gen2_resp.status_code == 200
        assert gen2_resp.json()["trip_summary"] == "Shared Itinerary for Tokyo"
        # Gemini call count must still be 1 (reused from cache!)
        assert mock_model.generate_content.call_count == 1

        # User 2's trip in DB also persisted the itinerary
        get2_resp = client.get(f"/api/v1/trips/{trip2_id}", headers=_auth_headers(user2_tokens))
        assert get2_resp.json()["itinerary"]["trip_summary"] == "Shared Itinerary for Tokyo"

    finally:
        _cleanup_user(user1_email)
        _cleanup_user(user2_email)


# ── 5. Expired / Missing Cache Falls Back to Gemini ───────────────────

@patch("google.generativeai.GenerativeModel")
@patch("app.services.ai_service.get_redis_client")
def test_expired_or_missing_cache_falls_back_to_gemini(mock_get_redis, mock_gen_model_class):
    fake_redis = InMemoryRedis()
    mock_get_redis.return_value = fake_redis

    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = _sample_itinerary("Fresh Gemini Itinerary").model_dump_json()
    mock_model.generate_content.return_value = mock_response
    mock_gen_model_class.return_value = mock_model

    start = date(2026, 10, 1)
    end = date(2026, 10, 1)

    # Initial state: fake_redis is empty (cache miss)
    result = generate_itinerary("Osaka", start, end)
    assert result.trip_summary == "Fresh Gemini Itinerary"
    assert mock_model.generate_content.call_count == 1

    # Simulate cache deletion / expiry
    key = compute_itinerary_cache_key("Osaka", start, end)
    fake_redis.delete(key)

    # Second call should call Gemini again
    result2 = generate_itinerary("Osaka", start, end)
    assert result2.trip_summary == "Fresh Gemini Itinerary"
    assert mock_model.generate_content.call_count == 2


# ── 6. Redis Failure Resilience ────────────────────────────────────────

@patch("google.generativeai.GenerativeModel")
@patch("app.services.ai_service.get_redis_client")
def test_redis_read_failure_gracefully_falls_back_to_gemini(mock_get_redis, mock_gen_model_class):
    """Redis read connection error falls back to Gemini without breaking the request."""
    broken_redis = MagicMock()
    broken_redis.get.side_effect = redis.exceptions.ConnectionError("Redis connection refused")
    broken_redis.setex.side_effect = redis.exceptions.ConnectionError("Redis connection refused")
    mock_get_redis.return_value = broken_redis

    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = _sample_itinerary("Fallback Gemini Output").model_dump_json()
    mock_model.generate_content.return_value = mock_response
    mock_gen_model_class.return_value = mock_model

    result = generate_itinerary("Nagoya", date(2026, 10, 1), date(2026, 10, 2))
    assert result.trip_summary == "Fallback Gemini Output"
    mock_model.generate_content.assert_called_once()


@patch("google.generativeai.GenerativeModel")
@patch("app.services.ai_service.get_redis_client")
def test_redis_write_failure_does_not_break_generation(mock_get_redis, mock_gen_model_class):
    """Redis write error logs warning but still returns the generated itinerary."""
    failing_write_redis = MagicMock()
    failing_write_redis.get.return_value = None  # Cache miss
    failing_write_redis.setex.side_effect = redis.exceptions.TimeoutError("Redis write timeout")
    mock_get_redis.return_value = failing_write_redis

    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = _sample_itinerary("Valid Output Despite Write Error").model_dump_json()
    mock_model.generate_content.return_value = mock_response
    mock_gen_model_class.return_value = mock_model

    result = generate_itinerary("Sapporo", date(2026, 10, 1), date(2026, 10, 2))
    assert result.trip_summary == "Valid Output Despite Write Error"


@patch("google.generativeai.GenerativeModel")
@patch("app.services.ai_service.get_redis_client")
def test_redis_corrupted_data_falls_back_to_gemini(mock_get_redis, mock_gen_model_class):
    """Corrupted JSON in Redis is safely discarded and falls back to Gemini."""
    corrupted_redis = InMemoryRedis()
    key = compute_itinerary_cache_key("Fukuoka", date(2026, 10, 1), date(2026, 10, 2))
    corrupted_redis.set(key, "{ corrupt json ...")
    mock_get_redis.return_value = corrupted_redis

    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = _sample_itinerary("Recovered from Corrupt Cache").model_dump_json()
    mock_model.generate_content.return_value = mock_response
    mock_gen_model_class.return_value = mock_model

    result = generate_itinerary("Fukuoka", date(2026, 10, 1), date(2026, 10, 2))
    assert result.trip_summary == "Recovered from Corrupt Cache"
    mock_model.generate_content.assert_called_once()


# ── 7. Failed Gemini Responses Are NOT Cached ──────────────────────────

@patch("google.generativeai.GenerativeModel")
@patch("app.services.ai_service.get_redis_client")
def test_failed_gemini_response_is_not_cached(mock_get_redis, mock_gen_model_class):
    """If Gemini fails, Redis is NOT updated with any key."""
    fake_redis = InMemoryRedis()
    mock_get_redis.return_value = fake_redis

    mock_model = MagicMock()
    mock_model.generate_content.side_effect = Exception("Gemini API 500 internal error")
    mock_gen_model_class.return_value = mock_model

    start = date(2026, 10, 1)
    end = date(2026, 10, 2)

    with pytest.raises(AIServiceError):
        generate_itinerary("Kobe", start, end)

    key = compute_itinerary_cache_key("Kobe", start, end)
    assert key not in fake_redis.store


# ── 8. Configurable TTL Verification ───────────────────────────────────

@patch("app.services.ai_service.get_redis_client")
def test_set_cached_itinerary_custom_ttl(mock_get_redis):
    fake_redis = InMemoryRedis()
    mock_get_redis.return_value = fake_redis

    sample = _sample_itinerary()
    success = set_cached_itinerary("itinerary:testkey", sample, ttl=7200)

    assert success is True
    assert fake_redis.ttls.get("itinerary:testkey") == 7200
