import hashlib
import json
import logging
from datetime import date
from typing import Any, Optional

import google.generativeai as genai
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.models.preference import UserPreference
from app.schemas.itinerary import ItinerarySchema
from app.schemas.recommendation import RecommendationsResponse

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Exception raised for errors in the AI service."""
    pass


# Hand-crafted Gemini-compatible schema for Itinerary — no "default" or "default_factory"
_ITINERARY_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "trip_summary": {"type": "string"},
        "days": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "activities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "approximate_time": {"type": "string"},
                                "location": {"type": "string"},
                            },
                            "required": ["title", "description", "approximate_time"],
                        },
                    },
                },
                "required": ["date", "activities"],
            },
        },
    },
    "required": ["trip_summary", "days"],
}


# Hand-crafted Gemini-compatible schema for Destination Recommendations
_RECOMMENDATION_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string"},
        "destination": {"type": "string"},
        "tagline": {"type": "string"},
        "reason": {"type": "string"},
        "highlights": {
            "type": "array",
            "items": {"type": "string"},
        },
        "image_search_term": {"type": "string"},
    },
    "required": ["category", "destination", "tagline", "reason", "highlights", "image_search_term"],
}

_RECOMMENDATIONS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "seasonal_pick": _RECOMMENDATION_ITEM_SCHEMA,
        "hidden_gem": _RECOMMENDATION_ITEM_SCHEMA,
        "experience_pick": _RECOMMENDATION_ITEM_SCHEMA,
    },
    "required": ["seasonal_pick", "hidden_gem", "experience_pick"],
}


def _normalize_text(val: Optional[str]) -> Optional[str]:
    """Strip whitespace and lowercase text, returning None if empty."""
    if val is None:
        return None
    cleaned = str(val).strip()
    return cleaned.lower() if cleaned else None


def _normalize_pref_enum(val: Any) -> Optional[str]:
    """Normalize preference enum values, treating 'no_preference' as None."""
    if val is None:
        return None
    raw = val.value if hasattr(val, "value") else str(val)
    raw = raw.strip().lower()
    if raw in ("", "no_preference", "none"):
        return None
    return raw


def _normalize_interests(val: Optional[str]) -> Optional[str]:
    """Normalize comma-separated interests by trimming, lowercasing, and sorting tags."""
    if val is None:
        return None
    cleaned = str(val).strip()
    if not cleaned:
        return None
    tags = [t.strip().lower() for t in cleaned.split(",") if t.strip()]
    if not tags:
        return None
    return ", ".join(sorted(tags))


def compute_itinerary_cache_key(
    destination: str,
    start_date: date,
    end_date: date,
    preferences: Optional[UserPreference] = None,
    num_travellers: Optional[int] = None,
    budget: Optional[str] = None,
    special_requirements: Optional[str] = None,
) -> str:
    """Compute a deterministic, normalized SHA-256 cache key for itinerary generation inputs.

    Note: user_id is explicitly NOT part of the cache key so that equivalent requests
    across different users can reuse the same cached itinerary.
    """
    food = None
    drinking = None
    style = None
    pace = None
    accommodation = None
    interests = None
    additional = None

    if preferences is not None:
        if isinstance(preferences, dict):
            food = _normalize_pref_enum(preferences.get("food_preference"))
            drinking = _normalize_pref_enum(preferences.get("drinking_preference"))
            style = _normalize_pref_enum(preferences.get("travel_style"))
            pace = _normalize_pref_enum(preferences.get("travel_pace"))
            accommodation = _normalize_pref_enum(preferences.get("accommodation_preference"))
            interests = _normalize_interests(preferences.get("interests"))
            additional = _normalize_text(preferences.get("additional_preferences"))
        else:
            food = _normalize_pref_enum(getattr(preferences, "food_preference", None))
            drinking = _normalize_pref_enum(getattr(preferences, "drinking_preference", None))
            style = _normalize_pref_enum(getattr(preferences, "travel_style", None))
            pace = _normalize_pref_enum(getattr(preferences, "travel_pace", None))
            accommodation = _normalize_pref_enum(getattr(preferences, "accommodation_preference", None))
            interests = _normalize_interests(getattr(preferences, "interests", None))
            additional = _normalize_text(getattr(preferences, "additional_preferences", None))

    key_payload = {
        "destination": _normalize_text(destination),
        "start_date": start_date.isoformat() if hasattr(start_date, "isoformat") else str(start_date),
        "end_date": end_date.isoformat() if hasattr(end_date, "isoformat") else str(end_date),
        "num_travellers": int(num_travellers) if num_travellers is not None else None,
        "budget": _normalize_text(budget),
        "special_requirements": _normalize_text(special_requirements),
        "preferences": {
            "food": food,
            "drinking": drinking,
            "style": style,
            "pace": pace,
            "accommodation": accommodation,
            "interests": interests,
            "additional": additional,
        },
    }

    serialized_payload = json.dumps(key_payload, sort_keys=True, separators=(",", ":"))
    key_hash = hashlib.sha256(serialized_payload.encode("utf-8")).hexdigest()
    return f"itinerary:{key_hash}"


def get_cached_itinerary(cache_key: str) -> Optional[ItinerarySchema]:
    """Retrieve and deserialize a cached itinerary from Redis.

    Returns None on cache miss or if Redis is unreachable / errors out.
    """
    try:
        client = get_redis_client()
        if not client:
            return None
        cached_data = client.get(cache_key)
        if not cached_data:
            return None
        data = json.loads(cached_data)
        return ItinerarySchema.model_validate(data)
    except Exception as e:
        logger.warning(f"Redis cache read error for key '{cache_key}': {e}")
        return None


def set_cached_itinerary(
    cache_key: str,
    itinerary: ItinerarySchema,
    ttl: Optional[int] = None,
) -> bool:
    """Serialize and store a structured itinerary in Redis with a TTL.

    Returns True on success, False if Redis is unreachable / errors out.
    """
    try:
        client = get_redis_client()
        if not client:
            return False
        settings = get_settings()
        cache_ttl = ttl if ttl is not None else settings.REDIS_CACHE_TTL
        serialized = itinerary.model_dump_json()
        if cache_ttl and cache_ttl > 0:
            client.setex(cache_key, cache_ttl, serialized)
        else:
            client.set(cache_key, serialized)
        logger.info(f"itinerary cache SET for key: {cache_key} (TTL={cache_ttl}s)")
        return True
    except Exception as e:
        logger.warning(f"Redis cache write error for key '{cache_key}': {e}")
        return False


def build_itinerary_prompt(
    destination: str,
    start_date: date,
    end_date: date,
    preferences: Optional[UserPreference] = None,
    num_travellers: Optional[int] = None,
    budget: Optional[str] = None,
    special_requirements: Optional[str] = None,
) -> str:
    """Construct a prompt for itinerary generation based on destination, dates, preferences, and planning details."""
    duration_days = (end_date - start_date).days + 1

    prompt_parts = [
        "You are an expert travel planner.",
        f"Generate a detailed daily itinerary for a trip to {destination}.",
        f"Trip Duration: {duration_days} days (from {start_date} to {end_date}).",
    ]

    planning_details = []
    if num_travellers:
        planning_details.append(f"- Number of travellers: {num_travellers}")
    if budget:
        planning_details.append(f"- Estimated Budget: {budget}")
    if special_requirements:
        planning_details.append(f"- Special requirements / notes: {special_requirements}")

    if planning_details:
        prompt_parts.append("\nTrip-specific details:")
        prompt_parts.extend(planning_details)

    if preferences:
        pref_details = []
        if preferences.food_preference and preferences.food_preference.value != "no_preference":
            pref_details.append(f"- Food preference: {preferences.food_preference.value}")
        if preferences.drinking_preference and preferences.drinking_preference.value != "no_preference":
            pref_details.append(f"- Drinking preference: {preferences.drinking_preference.value}")
        if preferences.travel_style:
            pref_details.append(f"- Travel style: {preferences.travel_style.value}")
        if preferences.travel_pace:
            pref_details.append(f"- Travel pace: {preferences.travel_pace.value}")
        if preferences.accommodation_preference and preferences.accommodation_preference.value != "no_preference":
            pref_details.append(f"- Accommodation: {preferences.accommodation_preference.value}")
        if preferences.interests:
            pref_details.append(f"- Interests: {preferences.interests}")
        if preferences.additional_preferences:
            pref_details.append(f"- Additional details: {preferences.additional_preferences}")

        if pref_details:
            prompt_parts.append("\nUser travel preferences to accommodate:")
            prompt_parts.extend(pref_details)

    prompt_parts.extend([
        "\nYou MUST respond with valid JSON that matches the following schema exactly:",
        "{",
        '  "trip_summary": "string summary of the entire trip",',
        '  "days": [',
        "    {",
        '      "date": "YYYY-MM-DD",',
        '      "activities": [',
        "        {",
        '          "title": "activity title",',
        '          "description": "activity description",',
        '          "approximate_time": "approximate time or order",',
        '          "location": "location name or null"',
        "        }",
        "      ]",
        "    }",
        "  ]",
        "}",
        "\nProvide high-quality, realistic activities. Make sure all dates in the response are consecutive and within the trip range.",
    ])

    return "\n".join(prompt_parts)


def generate_itinerary(
    destination: str,
    start_date: date,
    end_date: date,
    preferences: Optional[UserPreference] = None,
    num_travellers: Optional[int] = None,
    budget: Optional[str] = None,
    special_requirements: Optional[str] = None,
) -> ItinerarySchema:
    """Generate a structured travel itinerary using Redis cache or the Gemini API."""
    # 1. Compute deterministic cache key
    cache_key = compute_itinerary_cache_key(
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        preferences=preferences,
        num_travellers=num_travellers,
        budget=budget,
        special_requirements=special_requirements,
    )

    # 2. Check Redis cache first (Cache hit → return cached itinerary without calling Gemini)
    cached_itinerary = get_cached_itinerary(cache_key)
    if cached_itinerary is not None:
        logger.info(f"itinerary cache HIT for key: {cache_key}")
        return cached_itinerary

    logger.info(f"itinerary cache MISS for key: {cache_key}. Calling Gemini API...")

    # 3. Cache miss: Validate settings and call Gemini API
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        raise AIServiceError("GEMINI_API_KEY is not configured.")

    prompt = build_itinerary_prompt(
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        preferences=preferences,
        num_travellers=num_travellers,
        budget=budget,
        special_requirements=special_requirements,
    )

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                response_schema=_ITINERARY_RESPONSE_SCHEMA,
            ),
        )

        if not response.text:
            raise AIServiceError("Received empty response from Gemini API.")

        data = json.loads(response.text)
        itinerary = ItinerarySchema.model_validate(data)

        # 4. Successful Gemini response & validation: persist in Redis cache
        set_cached_itinerary(cache_key, itinerary)

        return itinerary

    except json.JSONDecodeError as e:
        raise AIServiceError(f"Failed to parse JSON response from Gemini: {e}")
    except ValidationError as e:
        raise AIServiceError(f"Gemini response did not match the expected schema: {e}")
    except AIServiceError:
        raise
    except Exception as e:
        raise AIServiceError(f"An unexpected error occurred during Gemini API call: {e}")


def compute_recommendations_cache_key(
    preferences: Optional[UserPreference] = None,
    target_date: Optional[date] = None,
) -> str:
    """Compute a deterministic, normalized SHA-256 cache key for destination recommendations / travel suggestions.

    Note: user_id is explicitly NOT part of the cache key so that equivalent requests
    across different users can reuse the same cached recommendations.
    """
    period_date = target_date or date.today()
    period_str = period_date.isoformat() if hasattr(period_date, "isoformat") else str(period_date)

    food = None
    drinking = None
    style = None
    pace = None
    accommodation = None
    interests = None
    additional = None

    if preferences is not None:
        if isinstance(preferences, dict):
            food = _normalize_pref_enum(preferences.get("food_preference"))
            drinking = _normalize_pref_enum(preferences.get("drinking_preference"))
            style = _normalize_pref_enum(preferences.get("travel_style"))
            pace = _normalize_pref_enum(preferences.get("travel_pace"))
            accommodation = _normalize_pref_enum(preferences.get("accommodation_preference"))
            interests = _normalize_interests(preferences.get("interests"))
            additional = _normalize_text(preferences.get("additional_preferences"))
        else:
            food = _normalize_pref_enum(getattr(preferences, "food_preference", None))
            drinking = _normalize_pref_enum(getattr(preferences, "drinking_preference", None))
            style = _normalize_pref_enum(getattr(preferences, "travel_style", None))
            pace = _normalize_pref_enum(getattr(preferences, "travel_pace", None))
            accommodation = _normalize_pref_enum(getattr(preferences, "accommodation_preference", None))
            interests = _normalize_interests(getattr(preferences, "interests", None))
            additional = _normalize_text(getattr(preferences, "additional_preferences", None))

    key_payload = {
        "date_period": period_str,
        "preferences": {
            "food": food,
            "drinking": drinking,
            "style": style,
            "pace": pace,
            "accommodation": accommodation,
            "interests": interests,
            "additional": additional,
        },
    }

    serialized_payload = json.dumps(key_payload, sort_keys=True, separators=(",", ":"))
    key_hash = hashlib.sha256(serialized_payload.encode("utf-8")).hexdigest()
    return f"suggestions:{key_hash}"


def get_cached_recommendations(cache_key: str) -> Optional[RecommendationsResponse]:
    """Retrieve and deserialize cached recommendations from Redis.

    Returns None on cache miss or if Redis is unreachable / errors out.
    """
    try:
        client = get_redis_client()
        if not client:
            return None
        cached_data = client.get(cache_key)
        if not cached_data:
            return None
        data = json.loads(cached_data)
        return RecommendationsResponse.model_validate(data)
    except Exception as e:
        logger.warning(f"Redis cache read error for key '{cache_key}': {e}")
        return None


def set_cached_recommendations(
    cache_key: str,
    recommendations: RecommendationsResponse,
    ttl: Optional[int] = None,
) -> bool:
    """Serialize and store recommendations in Redis with a TTL.

    Returns True on success, False if Redis is unreachable / errors out.
    """
    try:
        client = get_redis_client()
        if not client:
            return False
        settings = get_settings()
        cache_ttl = (
            ttl
            if ttl is not None
            else getattr(settings, "REDIS_RECOMMENDATION_CACHE_TTL", settings.REDIS_CACHE_TTL)
        )
        serialized = recommendations.model_dump_json()
        if cache_ttl and cache_ttl > 0:
            client.setex(cache_key, cache_ttl, serialized)
        else:
            client.set(cache_key, serialized)
        logger.info(f"suggestions cache SET for key: {cache_key} (TTL={cache_ttl}s)")
        return True
    except Exception as e:
        logger.warning(f"Redis cache write error for key '{cache_key}': {e}")
        return False


def build_recommendations_prompt(
    preferences: Optional[UserPreference] = None,
    target_date: Optional[date] = None,
) -> str:
    """Construct a prompt for 3 structured destination recommendations based on current date/season and user preferences."""
    today = target_date or date.today()
    month_name = today.strftime("%B")

    prompt_parts = [
        "You are an expert travel advisor.",
        f"Current Date: {today.isoformat()} (Month: {month_name}).",
        "Generate exactly 3 top destination recommendations tailored to this time of year and the user's travel preferences.",
        "You MUST provide exactly 3 picks matching these categories:",
        "1. 'Seasonal Pick': The optimal destination to visit during this current month/season.",
        "2. 'Hidden Gem': An off-the-beaten-path destination free from excessive crowds.",
        "3. 'Experience Pick': A destination famous for an immersive cultural or adventure experience.",
        "\nFor EACH recommendation pick, you MUST provide an 'image_search_term' representing a famous, highly recognizable landmark, natural attraction, or scenic spot at that destination (e.g. 'Dal Lake Kashmir', 'Fushimi Inari Kyoto', 'Rishikesh Ganges river'). Do NOT use generic terms like 'Kashmir travel'.",
    ]

    if preferences:
        pref_details = []
        if preferences.food_preference and preferences.food_preference.value != "no_preference":
            pref_details.append(f"- Food preference: {preferences.food_preference.value}")
        if preferences.drinking_preference and preferences.drinking_preference.value != "no_preference":
            pref_details.append(f"- Drinking preference: {preferences.drinking_preference.value}")
        if preferences.travel_style:
            pref_details.append(f"- Travel style: {preferences.travel_style.value}")
        if preferences.travel_pace:
            pref_details.append(f"- Travel pace: {preferences.travel_pace.value}")
        if preferences.accommodation_preference and preferences.accommodation_preference.value != "no_preference":
            pref_details.append(f"- Accommodation: {preferences.accommodation_preference.value}")
        if preferences.interests:
            pref_details.append(f"- Interests: {preferences.interests}")
        if preferences.additional_preferences:
            pref_details.append(f"- Additional details: {preferences.additional_preferences}")

        if pref_details:
            prompt_parts.append("\nUser travel preferences to incorporate:")
            prompt_parts.extend(pref_details)

    prompt_parts.append("\nYou MUST return valid JSON conforming strictly to the requested schema.")
    return "\n".join(prompt_parts)


def generate_recommendations(
    preferences: Optional[UserPreference] = None,
    target_date: Optional[date] = None,
) -> RecommendationsResponse:
    """Generate 3 structured destination recommendations (Seasonal, Hidden Gem, Experience) using Redis cache or Gemini."""
    # 1. Compute deterministic cache key
    cache_key = compute_recommendations_cache_key(
        preferences=preferences,
        target_date=target_date,
    )

    # 2. Check Redis cache first (Cache hit → return cached recommendations without calling Gemini)
    cached_recs = get_cached_recommendations(cache_key)
    if cached_recs is not None:
        logger.info(f"suggestions cache HIT for key: {cache_key}")
        return cached_recs

    logger.info(f"suggestions cache MISS for key: {cache_key}. Calling Gemini API...")

    # 3. Cache miss: Validate settings and call Gemini API
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        raise AIServiceError("GEMINI_API_KEY is not configured.")

    prompt = build_recommendations_prompt(preferences=preferences, target_date=target_date)

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                response_schema=_RECOMMENDATIONS_RESPONSE_SCHEMA,
            ),
        )

        if not response.text:
            raise AIServiceError("Received empty response from Gemini API for recommendations.")

        data = json.loads(response.text)
        recommendations = RecommendationsResponse.model_validate(data)

        # 4. Successful Gemini response & validation: persist in Redis cache
        set_cached_recommendations(cache_key, recommendations)

        return recommendations

    except json.JSONDecodeError as e:
        raise AIServiceError(f"Failed to parse JSON response from Gemini for recommendations: {e}")
    except ValidationError as e:
        raise AIServiceError(f"Gemini recommendations response did not match expected schema: {e}")
    except AIServiceError:
        raise
    except Exception as e:
        raise AIServiceError(f"An unexpected error occurred during Gemini recommendations call: {e}")
