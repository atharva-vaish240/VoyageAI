"""User travel preferences model — one record per user."""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Enum,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class FoodPreference(str, enum.Enum):
    VEGETARIAN = "vegetarian"
    NON_VEGETARIAN = "non_vegetarian"
    VEGAN = "vegan"
    NO_PREFERENCE = "no_preference"


class DrinkingPreference(str, enum.Enum):
    DRINKER = "drinker"
    NON_DRINKER = "non_drinker"
    NO_PREFERENCE = "no_preference"


class TravelStyle(str, enum.Enum):
    ADVENTURE = "adventure"
    RELAXED = "relaxed"
    CULTURAL = "cultural"
    LUXURY = "luxury"
    BUDGET = "budget"
    MIXED = "mixed"


class TravelPace(str, enum.Enum):
    RELAXED = "relaxed"
    MODERATE = "moderate"
    PACKED = "packed"


class AccommodationPreference(str, enum.Enum):
    HOTEL = "hotel"
    HOSTEL = "hostel"
    RESORT = "resort"
    HOMESTAY = "homestay"
    NO_PREFERENCE = "no_preference"


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    food_preference = Column(
        Enum(FoodPreference), nullable=False, default=FoodPreference.NO_PREFERENCE
    )
    drinking_preference = Column(
        Enum(DrinkingPreference), nullable=False, default=DrinkingPreference.NO_PREFERENCE
    )
    travel_style = Column(
        Enum(TravelStyle), nullable=False, default=TravelStyle.MIXED
    )
    travel_pace = Column(
        Enum(TravelPace), nullable=False, default=TravelPace.MODERATE
    )
    accommodation_preference = Column(
        Enum(AccommodationPreference), nullable=False, default=AccommodationPreference.NO_PREFERENCE
    )

    # Comma-separated list of interests (simple, maintainable, no join table needed)
    interests = Column(String(500), nullable=False, default="")

    # Free-text field
    additional_preferences = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    user = relationship("User", back_populates="preferences")

    def __repr__(self):
        return f"<UserPreference id={self.id} user_id={self.user_id}>"
