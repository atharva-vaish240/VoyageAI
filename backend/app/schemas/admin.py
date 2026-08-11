"""Pydantic schemas for admin endpoints."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models.trip import TripStatus
from app.schemas.itinerary import ItinerarySchema
from app.schemas.recommendation import RecommendationImage


class AdminUserSummary(BaseModel):
    id: int
    name: str
    email: str

    model_config = {"from_attributes": True}


class AdminTripResponse(BaseModel):
    """Lightweight response for admin trip list across all users."""
    id: int
    user_id: int
    user: Optional[AdminUserSummary] = None
    title: str
    destination: Optional[str] = None
    start_date: date
    end_date: date
    status: TripStatus
    num_travellers: Optional[int] = None
    budget: Optional[str] = None
    special_requirements: Optional[str] = None
    destination_image: Optional[RecommendationImage] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdminTripDetailResponse(AdminTripResponse):
    """Detailed response for single trip view for admin, including read-only itinerary."""
    itinerary: Optional[ItinerarySchema] = None


class AdminTripUpdate(BaseModel):
    """Metadata update schema for admin.
    
    Excludes generated fields (itinerary, destination_image, etc.).
    """
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    destination: Optional[str] = Field(None, max_length=200)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[TripStatus] = None
    num_travellers: Optional[int] = Field(None, ge=1)
    budget: Optional[str] = Field(None, max_length=100)
    special_requirements: Optional[str] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self
