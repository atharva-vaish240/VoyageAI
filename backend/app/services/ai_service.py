"""AI Service for itinerary generation using Gemini."""

from datetime import date
import json
from typing import Optional

import google.generativeai as genai
from pydantic import ValidationError

from app.core.config import get_settings
from app.models.preference import UserPreference
from app.schemas.itinerary import ItinerarySchema


class AIServiceError(Exception):
    """Exception raised for errors in the AI service."""
    pass


# Hand-crafted Gemini-compatible schema — no "default" or "default_factory"
# fields that the Gemini API rejects.  ItinerarySchema is still used to
# validate the parsed response on our side.
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


def build_itinerary_prompt(
    destination: str,
    start_date: date,
    end_date: date,
    preferences: Optional[UserPreference] = None,
) -> str:
    """Construct a prompt for itinerary generation based on destination, dates, and preferences."""
    duration_days = (end_date - start_date).days + 1

    prompt_parts = [
        "You are an expert travel planner.",
        f"Generate a detailed daily itinerary for a trip to {destination}.",
        f"Trip Duration: {duration_days} days (from {start_date} to {end_date}).",
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
) -> ItinerarySchema:
    """Generate a structured travel itinerary using the Gemini API."""
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        raise AIServiceError("GEMINI_API_KEY is not configured.")

    prompt = build_itinerary_prompt(destination, start_date, end_date, preferences)

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
        return ItinerarySchema.model_validate(data)

    except json.JSONDecodeError as e:
        raise AIServiceError(f"Failed to parse JSON response from Gemini: {e}")
    except ValidationError as e:
        raise AIServiceError(f"Gemini response did not match the expected schema: {e}")
    except AIServiceError:
        raise  # Re-raise our own errors without wrapping them
    except Exception as e:
        raise AIServiceError(f"An unexpected error occurred during Gemini API call: {e}")
