"""Focused tests for Redis caching in the destination recommendations flow."""

import json
from datetime import date
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
from app.models.user import RefreshToken, User
from app.schemas.recommendation import (
    RecommendationImage,
    RecommendationItem,
    RecommendationsResponse,
)
from app.services.ai_service import (
    AIServiceError,
    compute_recommendations_cache_key,
    generate_recommendations,
    get_cached_recommendations,
    set_cached_recommendations,
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


def _sample_recommendations(tagline: str = "Autumn leaves & historic temples") -> RecommendationsResponse:
    return RecommendationsResponse(
        seasonal_pick=RecommendationItem(
            category="Seasonal Pick",
            destination="Kyoto, Japan",
            tagline=tagline,
            reason="Peak foliage season.",
            highlights=["Kiyomizu-dera", "Arashiyama", "Fushimi Inari"],
            image_search_term="Fushimi Inari Kyoto",
        ),
        hidden_gem=RecommendationItem(
            category="Hidden Gem",
            destination="Tirthan Valley, India",
            tagline="Pristine alpine streams",
            reason="Uncrowded scenic beauty.",
            highlights=["Great Himalayan National Park", "Jibhi Waterfalls"],
            image_search_term="Tirthan Valley river",
        ),
        experience_pick=RecommendationItem(
            category="Experience Pick",
            destination="Rishikesh, India",
            tagline="Ganges rafting & spiritual retreats",
            reason="Vibrant yoga and adventure.",
            highlights=["Rafting", "Ganga Aarti"],
            image_search_term="Rishikesh Ganges river",
        ),
    )


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


def _signup_and_login(email: str, name: str = "Rec Test User", password: str = "TestPass123!"):
    client.post("/api/v1/auth/signup", json={"name": name, "email": email, "password": password})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()


def _auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


# ── 1. Deterministic Cache Key Generation ─────────────────────────────

def test_cache_key_generation_is_deterministic():
    """Identical recommendation inputs always produce the exact same cache key."""
    pref = UserPreference(
        food_preference=FoodPreference.VEGAN,
        travel_style=TravelStyle.CULTURAL,
        travel_pace=TravelPace.MODERATE,
        interests="temples, museums",
    )
    ref_date = date(2026, 8, 16)

    key1 = compute_recommendations_cache_key(preferences=pref, target_date=ref_date)
    key2 = compute_recommendations_cache_key(preferences=pref, target_date=ref_date)

    assert key1 == key2
    assert key1.startswith("suggestions:")


# ── 2. User ID is NOT Part of Cache Key ───────────────────────────────

def test_user_id_is_not_part_of_cache_key():
    """Two different users with different user_ids but identical preferences produce the exact same key."""
    pref_user_1 = UserPreference(
        user_id=101,
        food_preference=FoodPreference.VEGETARIAN,
        travel_style=TravelStyle.ADVENTURE,
        interests="hiking, mountains",
    )
    pref_user_2 = UserPreference(
        user_id=202,
        food_preference=FoodPreference.VEGETARIAN,
        travel_style=TravelStyle.ADVENTURE,
        interests="hiking, mountains",
    )
    ref_date = date(2026, 8, 16)

    key1 = compute_recommendations_cache_key(preferences=pref_user_1, target_date=ref_date)
    key2 = compute_recommendations_cache_key(preferences=pref_user_2, target_date=ref_date)

    assert key1 == key2
    assert "101" not in key1
    assert "202" not in key2


# ── 3. Equivalent Preferences Produce Same Key ────────────────────────

def test_equivalent_preferences_produce_same_key():
    """Whitespace, casing, comma-separated interest ordering, and 'no_preference' normalize to identical keys."""
    pref_a = UserPreference(
        food_preference=FoodPreference.NO_PREFERENCE,
        drinking_preference=DrinkingPreference.NO_PREFERENCE,
        accommodation_preference=AccommodationPreference.NO_PREFERENCE,
        travel_style=TravelStyle.RELAXED,
        interests="museums, temples, beaches",
        additional_preferences="  Near City Center  ",
    )
    pref_b = UserPreference(
        food_preference=None,
        drinking_preference=None,
        accommodation_preference=None,
        travel_style=TravelStyle.RELAXED,
        interests="  beaches ,  museums,temples  ",
        additional_preferences="near city center",
    )
    ref_date = date(2026, 8, 16)

    key_a = compute_recommendations_cache_key(preferences=pref_a, target_date=ref_date)
    key_b = compute_recommendations_cache_key(preferences=pref_b, target_date=ref_date)

    assert key_a == key_b


# ── 4. Different Preferences Produce Different Keys ───────────────────

def test_different_preferences_produce_different_keys():
    """Different food, travel style, pace, accommodation, or interests produce distinct keys."""
    ref_date = date(2026, 8, 16)
    key_none = compute_recommendations_cache_key(preferences=None, target_date=ref_date)

    pref_vegan = UserPreference(food_preference=FoodPreference.VEGAN)
    pref_non_veg = UserPreference(food_preference=FoodPreference.NON_VEGETARIAN)
    pref_adventure = UserPreference(travel_style=TravelStyle.ADVENTURE)
    pref_luxury = UserPreference(travel_style=TravelStyle.LUXURY)

    key_vegan = compute_recommendations_cache_key(preferences=pref_vegan, target_date=ref_date)
    key_non_veg = compute_recommendations_cache_key(preferences=pref_non_veg, target_date=ref_date)
    key_adventure = compute_recommendations_cache_key(preferences=pref_adventure, target_date=ref_date)
    key_luxury = compute_recommendations_cache_key(preferences=pref_luxury, target_date=ref_date)

    assert key_vegan != key_none
    assert key_vegan != key_non_veg
    assert key_adventure != key_luxury


# ── 5. Different Recommendation Periods / Dates Produce Different Keys 

def test_different_periods_produce_different_keys():
    """Different target dates/periods produce different cache keys."""
    pref = UserPreference(travel_style=TravelStyle.RELAXED)
    key_summer = compute_recommendations_cache_key(preferences=pref, target_date=date(2026, 8, 16))
    key_winter = compute_recommendations_cache_key(preferences=pref, target_date=date(2026, 12, 25))

    assert key_summer != key_winter


# ── 6. Cache Miss Calls Gemini & Stores in Redis ──────────────────────

@patch("google.generativeai.GenerativeModel")
@patch("app.services.ai_service.get_redis_client")
def test_cache_miss_calls_gemini_and_stores_in_redis(mock_get_redis, mock_gen_model_class):
    fake_redis = InMemoryRedis()
    mock_get_redis.return_value = fake_redis

    mock_model = MagicMock()
    mock_response = MagicMock()
    sample = _sample_recommendations("Fresh Gemini Recommendations")
    mock_response.text = sample.model_dump_json()
    mock_model.generate_content.return_value = mock_response
    mock_gen_model_class.return_value = mock_model

    pref = UserPreference(food_preference=FoodPreference.VEGAN)
    ref_date = date(2026, 8, 16)

    result = generate_recommendations(preferences=pref, target_date=ref_date)

    # Gemini was called
    mock_model.generate_content.assert_called_once()
    assert result.seasonal_pick.tagline == "Fresh Gemini Recommendations"

    # Result was saved in Redis
    key = compute_recommendations_cache_key(preferences=pref, target_date=ref_date)
    assert key in fake_redis.store
    stored_json = json.loads(fake_redis.store[key])
    assert stored_json["seasonal_pick"]["tagline"] == "Fresh Gemini Recommendations"
    # Check TTL is set to configured recommendation cache TTL
    assert fake_redis.ttls.get(key) == get_settings().REDIS_RECOMMENDATION_CACHE_TTL


# ── 7. Cache Hit Does Not Call Gemini ──────────────────────────────────

@patch("google.generativeai.GenerativeModel")
@patch("app.services.ai_service.get_redis_client")
def test_cache_hit_does_not_call_gemini(mock_get_redis, mock_gen_model_class):
    fake_redis = InMemoryRedis()
    mock_get_redis.return_value = fake_redis

    pref = UserPreference(food_preference=FoodPreference.VEGAN)
    ref_date = date(2026, 8, 16)
    key = compute_recommendations_cache_key(preferences=pref, target_date=ref_date)

    # Pre-populate Redis with cached recommendations
    cached_obj = _sample_recommendations("Cached Summer Picks")
    fake_redis.setex(key, 14400, cached_obj.model_dump_json())

    result = generate_recommendations(preferences=pref, target_date=ref_date)

    # Gemini model is never instantiated or called
    mock_gen_model_class.assert_not_called()
    assert result.seasonal_pick.tagline == "Cached Summer Picks"


# ── 8. Cross-User Cache Reuse (Integration Test) ───────────────────────

@patch("google.generativeai.GenerativeModel")
@patch("app.services.ai_service.get_redis_client")
def test_cross_user_cache_reuse_endpoint(mock_get_redis, mock_gen_model_class):
    """User 1 calls /recommendations (miss -> Gemini -> stored in Redis).
    User 2 with equivalent preferences calls /recommendations (hit -> Redis -> Gemini NOT called again)."""
    fake_redis = InMemoryRedis()
    mock_get_redis.return_value = fake_redis

    mock_model = MagicMock()
    mock_response = MagicMock()
    sample = _sample_recommendations("Shared AI Recommendations")
    mock_response.text = sample.model_dump_json()
    mock_model.generate_content.return_value = mock_response
    mock_gen_model_class.return_value = mock_model

    user1_email = "user1_rec_cache@test.com"
    user2_email = "user2_rec_cache@test.com"
    _cleanup_user(user1_email)
    _cleanup_user(user2_email)

    try:
        user1_tokens = _signup_and_login(user1_email, name="User One")
        user2_tokens = _signup_and_login(user2_email, name="User Two")

        # Set identical preferences for both users
        pref_payload = {"food_preference": "vegan", "travel_style": "cultural"}
        client.put("/api/v1/preferences", json=pref_payload, headers=_auth_headers(user1_tokens))
        client.put("/api/v1/preferences", json=pref_payload, headers=_auth_headers(user2_tokens))

        # 1. User 1 calls recommendations -> Cache Miss -> Gemini called
        rec1_resp = client.post("/api/v1/recommendations", headers=_auth_headers(user1_tokens))
        assert rec1_resp.status_code == 200
        assert rec1_resp.json()["seasonal_pick"]["tagline"] == "Shared AI Recommendations"
        assert mock_model.generate_content.call_count == 1

        # 2. User 2 calls recommendations -> Cache Hit -> Gemini NOT called again
        rec2_resp = client.post("/api/v1/recommendations", headers=_auth_headers(user2_tokens))
        assert rec2_resp.status_code == 200
        assert rec2_resp.json()["seasonal_pick"]["tagline"] == "Shared AI Recommendations"
        # Gemini call count must still be 1 (reused from cache!)
        assert mock_model.generate_content.call_count == 1

    finally:
        _cleanup_user(user1_email)
        _cleanup_user(user2_email)


# ── 9. Expired / Missing Cache Falls Back to Gemini ───────────────────

@patch("google.generativeai.GenerativeModel")
@patch("app.services.ai_service.get_redis_client")
def test_expired_or_missing_cache_falls_back_to_gemini(mock_get_redis, mock_gen_model_class):
    fake_redis = InMemoryRedis()
    mock_get_redis.return_value = fake_redis

    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = _sample_recommendations("Fresh Output").model_dump_json()
    mock_model.generate_content.return_value = mock_response
    mock_gen_model_class.return_value = mock_model

    pref = UserPreference(travel_style=TravelStyle.RELAXED)
    ref_date = date(2026, 8, 16)

    # Initial state: fake_redis is empty (cache miss)
    result = generate_recommendations(preferences=pref, target_date=ref_date)
    assert result.seasonal_pick.tagline == "Fresh Output"
    assert mock_model.generate_content.call_count == 1

    # Simulate cache eviction / expiry
    key = compute_recommendations_cache_key(preferences=pref, target_date=ref_date)
    fake_redis.delete(key)

    # Second call should invoke Gemini again
    result2 = generate_recommendations(preferences=pref, target_date=ref_date)
    assert result2.seasonal_pick.tagline == "Fresh Output"
    assert mock_model.generate_content.call_count == 2


# ── 10. Redis GET Failure Gracefully Falls Back to Gemini ─────────────

@patch("google.generativeai.GenerativeModel")
@patch("app.services.ai_service.get_redis_client")
def test_redis_get_failure_gracefully_falls_back_to_gemini(mock_get_redis, mock_gen_model_class):
    """Redis read connection error logs warning and falls back to Gemini."""
    broken_redis = MagicMock()
    broken_redis.get.side_effect = redis.exceptions.ConnectionError("Redis connection refused")
    broken_redis.setex.side_effect = redis.exceptions.ConnectionError("Redis connection refused")
    mock_get_redis.return_value = broken_redis

    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = _sample_recommendations("Fallback Gemini Output").model_dump_json()
    mock_model.generate_content.return_value = mock_response
    mock_gen_model_class.return_value = mock_model

    result = generate_recommendations(preferences=None, target_date=date(2026, 8, 16))
    assert result.seasonal_pick.tagline == "Fallback Gemini Output"
    mock_model.generate_content.assert_called_once()


# ── 11. Redis SET Failure Does Not Break Request ───────────────────────

@patch("google.generativeai.GenerativeModel")
@patch("app.services.ai_service.get_redis_client")
def test_redis_set_failure_does_not_break_generation(mock_get_redis, mock_gen_model_class):
    """Redis write error logs warning but still returns generated recommendations."""
    failing_write_redis = MagicMock()
    failing_write_redis.get.return_value = None  # Cache miss
    failing_write_redis.setex.side_effect = redis.exceptions.TimeoutError("Redis write timeout")
    mock_get_redis.return_value = failing_write_redis

    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = _sample_recommendations("Valid Output Despite Write Error").model_dump_json()
    mock_model.generate_content.return_value = mock_response
    mock_gen_model_class.return_value = mock_model

    result = generate_recommendations(preferences=None, target_date=date(2026, 8, 16))
    assert result.seasonal_pick.tagline == "Valid Output Despite Write Error"


# ── 12. Corrupted Cached JSON Falls Back to Gemini ─────────────────────

@patch("google.generativeai.GenerativeModel")
@patch("app.services.ai_service.get_redis_client")
def test_redis_corrupted_data_falls_back_to_gemini(mock_get_redis, mock_gen_model_class):
    """Corrupted JSON in Redis is safely ignored and falls back to Gemini."""
    corrupted_redis = InMemoryRedis()
    key = compute_recommendations_cache_key(preferences=None, target_date=date(2026, 8, 16))
    corrupted_redis.set(key, "{ corrupt recommendations json ...")
    mock_get_redis.return_value = corrupted_redis

    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = _sample_recommendations("Recovered from Corrupted Cache").model_dump_json()
    mock_model.generate_content.return_value = mock_response
    mock_gen_model_class.return_value = mock_model

    result = generate_recommendations(preferences=None, target_date=date(2026, 8, 16))
    assert result.seasonal_pick.tagline == "Recovered from Corrupted Cache"
    mock_model.generate_content.assert_called_once()


# ── 13. Failed Gemini Responses Are NOT Cached ─────────────────────────

@patch("google.generativeai.GenerativeModel")
@patch("app.services.ai_service.get_redis_client")
def test_failed_gemini_response_is_not_cached(mock_get_redis, mock_gen_model_class):
    """If Gemini fails, Redis is NOT updated with any key."""
    fake_redis = InMemoryRedis()
    mock_get_redis.return_value = fake_redis

    mock_model = MagicMock()
    mock_model.generate_content.side_effect = Exception("Gemini API error 500")
    mock_gen_model_class.return_value = mock_model

    pref = UserPreference(travel_style=TravelStyle.ADVENTURE)
    ref_date = date(2026, 8, 16)

    with pytest.raises(AIServiceError):
        generate_recommendations(preferences=pref, target_date=ref_date)

    key = compute_recommendations_cache_key(preferences=pref, target_date=ref_date)
    assert key not in fake_redis.store


# ── 14. Custom TTL is Respected ────────────────────────────────────────

@patch("app.services.ai_service.get_redis_client")
def test_set_cached_recommendations_custom_ttl(mock_get_redis):
    """Custom TTL passed to set_cached_recommendations is respected."""
    fake_redis = InMemoryRedis()
    mock_get_redis.return_value = fake_redis

    sample = _sample_recommendations()
    success = set_cached_recommendations("suggestions:custom_ttl_key", sample, ttl=7200)

    assert success is True
    assert fake_redis.ttls.get("suggestions:custom_ttl_key") == 7200
