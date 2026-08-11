"""Unit tests for the AI itinerary generation service."""

from datetime import date
from unittest.mock import patch, MagicMock

import pytest
from pydantic import ValidationError

from app.models.preference import (
    UserPreference,
    FoodPreference,
    DrinkingPreference,
    TravelStyle,
    TravelPace,
    AccommodationPreference,
)
from app.services.ai_service import (
    build_itinerary_prompt,
    generate_itinerary,
    AIServiceError,
)
from app.schemas.itinerary import ItinerarySchema


# ── 1. Prompt Construction Tests ──────────────────────────────────────

def test_prompt_construction_without_preferences():
    start = date(2026, 10, 1)
    end = date(2026, 10, 5)
    prompt = build_itinerary_prompt("Tokyo", start, end)

    assert "Tokyo" in prompt
    assert "5 days" in prompt
    assert "2026-10-01" in prompt
    assert "2026-10-05" in prompt
    assert "User travel preferences to accommodate" not in prompt


def test_prompt_construction_with_preferences():
    start = date(2026, 10, 1)
    end = date(2026, 10, 5)
    
    # Create non-persistent UserPreference model
    pref = UserPreference(
        food_preference=FoodPreference.VEGAN,
        drinking_preference=DrinkingPreference.NON_DRINKER,
        travel_style=TravelStyle.ADVENTURE,
        travel_pace=TravelPace.PACKED,
        accommodation_preference=AccommodationPreference.HOSTEL,
        interests="hiking, temples, sushi",
        additional_preferences="Allergic to peanuts.",
    )

    prompt = build_itinerary_prompt("Tokyo", start, end, pref)

    assert "Tokyo" in prompt
    assert "vegan" in prompt
    assert "non_drinker" in prompt
    assert "adventure" in prompt
    assert "packed" in prompt
    assert "hostel" in prompt
    assert "hiking, temples, sushi" in prompt
    assert "Allergic to peanuts." in prompt


# ── 2. Mocked API Success & Schema Parsing Tests ──────────────────────

@patch("google.generativeai.GenerativeModel")
@patch("app.services.ai_service.get_settings")
def test_generate_itinerary_success(mock_get_settings, mock_gen_model_class):
    # Configure mock settings with key
    mock_settings = MagicMock()
    mock_settings.GEMINI_API_KEY = "test_gemini_key"
    mock_get_settings.return_value = mock_settings

    # Configure mock Gemini response
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = """
    {
      "trip_summary": "An amazing adventure in Kyoto",
      "days": [
        {
          "date": "2026-11-01",
          "activities": [
            {
              "title": "Kinkaku-ji Temple",
              "description": "Visit the golden pavilion.",
              "approximate_time": "09:00 AM",
              "location": "Kyoto Golden Pavilion"
            }
          ]
        }
      ]
    }
    """
    mock_model.generate_content.return_value = mock_response
    mock_gen_model_class.return_value = mock_model

    # Run service function
    itinerary = generate_itinerary("Kyoto", date(2026, 11, 1), date(2026, 11, 1))

    assert isinstance(itinerary, ItinerarySchema)
    assert itinerary.trip_summary == "An amazing adventure in Kyoto"
    assert len(itinerary.days) == 1
    assert itinerary.days[0].date == date(2026, 11, 1)
    assert itinerary.days[0].activities[0].title == "Kinkaku-ji Temple"


# ── 3. Missing API Key Handling ──────────────────────────────────────

@patch("app.services.ai_service.get_settings")
def test_generate_itinerary_missing_key_raises(mock_get_settings):
    # Mock settings without API key
    mock_settings = MagicMock()
    mock_settings.GEMINI_API_KEY = ""
    mock_get_settings.return_value = mock_settings

    with pytest.raises(AIServiceError) as exc_info:
        generate_itinerary("Kyoto", date(2026, 11, 1), date(2026, 11, 1))
    
    assert "GEMINI_API_KEY is not configured" in str(exc_info.value)


# ── 4. Invalid AI Output Handling ─────────────────────────────────────

@patch("google.generativeai.GenerativeModel")
@patch("app.services.ai_service.get_settings")
def test_generate_itinerary_invalid_json_raises(mock_get_settings, mock_gen_model_class):
    mock_settings = MagicMock()
    mock_settings.GEMINI_API_KEY = "test_gemini_key"
    mock_get_settings.return_value = mock_settings

    mock_model = MagicMock()
    mock_response = MagicMock()
    # Invalid JSON string
    mock_response.text = "This is not JSON text at all."
    mock_model.generate_content.return_value = mock_response
    mock_gen_model_class.return_value = mock_model

    with pytest.raises(AIServiceError) as exc_info:
        generate_itinerary("Kyoto", date(2026, 11, 1), date(2026, 11, 1))
    
    assert "Failed to parse JSON response" in str(exc_info.value)


@patch("google.generativeai.GenerativeModel")
@patch("app.services.ai_service.get_settings")
def test_generate_itinerary_invalid_schema_raises(mock_get_settings, mock_gen_model_class):
    mock_settings = MagicMock()
    mock_settings.GEMINI_API_KEY = "test_gemini_key"
    mock_get_settings.return_value = mock_settings

    mock_model = MagicMock()
    mock_response = MagicMock()
    # JSON missing the required 'trip_summary' field
    mock_response.text = """
    {
      "days": []
    }
    """
    mock_model.generate_content.return_value = mock_response
    mock_gen_model_class.return_value = mock_model

    with pytest.raises(AIServiceError) as exc_info:
        generate_itinerary("Kyoto", date(2026, 11, 1), date(2026, 11, 1))
    
    assert "did not match the expected schema" in str(exc_info.value)
