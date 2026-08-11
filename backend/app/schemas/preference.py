"""Pydantic schemas for user travel preferences."""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models.preference import (
    FoodPreference,
    DrinkingPreference,
    TravelStyle,
    TravelPace,
    AccommodationPreference,
)


# ── Request / Update schema ─────────────────────────────────────

class PreferencesUpdate(BaseModel):
    """Create or fully replace preferences. All fields optional with defaults."""

    food_preference: FoodPreference = Field(
        default=FoodPreference.NO_PREFERENCE,
        description="vegetarian, non_vegetarian, vegan, no_preference",
    )
    drinking_preference: DrinkingPreference = Field(
        default=DrinkingPreference.NO_PREFERENCE,
        description="drinker, non_drinker, no_preference",
    )
    travel_style: TravelStyle = Field(
        default=TravelStyle.MIXED,
        description="adventure, relaxed, cultural, luxury, budget, mixed",
    )
    travel_pace: TravelPace = Field(
        default=TravelPace.MODERATE,
        description="relaxed, moderate, packed",
    )
    accommodation_preference: AccommodationPreference = Field(
        default=AccommodationPreference.NO_PREFERENCE,
        description="hotel, hostel, resort, homestay, no_preference",
    )
    interests: List[str] = Field(
        default_factory=list,
        description="List of interests, e.g. ['beaches', 'mountains', 'history']",
    )
    additional_preferences: Optional[str] = None


# ── Response schema ──────────────────────────────────────────────

class PreferencesResponse(BaseModel):
    id: int
    user_id: int
    food_preference: FoodPreference
    drinking_preference: DrinkingPreference
    travel_style: TravelStyle
    travel_pace: TravelPace
    accommodation_preference: AccommodationPreference
    interests: List[str]
    additional_preferences: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
