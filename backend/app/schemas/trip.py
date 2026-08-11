"""Pydantic schemas for trips."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models.trip import TripStatus
from app.schemas.itinerary import ItinerarySchema


# ── Request schemas ──────────────────────────────────────────────

class TripCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    destination: Optional[str] = Field(None, max_length=200)
    start_date: date
    end_date: date
    status: TripStatus = Field(default=TripStatus.DRAFT)
    num_travellers: Optional[int] = Field(None, ge=1)
    budget: Optional[str] = Field(None, max_length=100)
    special_requirements: Optional[str] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class TripUpdate(BaseModel):
    """Partial update — all fields optional."""
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


# ── Response schemas ─────────────────────────────────────────────

class TripResponse(BaseModel):
    """Lightweight response for trip lists."""
    id: int
    user_id: int
    title: str
    destination: Optional[str]
    start_date: date
    end_date: date
    status: TripStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TripDetailResponse(TripResponse):
    """Detailed response for single trip view, including planning info and itinerary."""
    num_travellers: Optional[int] = None
    budget: Optional[str] = None
    special_requirements: Optional[str] = None
    itinerary: Optional[ItinerarySchema] = None
