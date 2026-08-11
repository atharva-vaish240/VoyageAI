"""Pydantic schemas for AI-generated itineraries."""

import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ActivitySchema(BaseModel):
    title: str = Field(..., description="Title of the activity")
    description: str = Field(..., description="Description of what to do")
    approximate_time: str = Field(
        ...,
        description="Approximate time of day or order (e.g. '09:00 AM', 'Morning', '1')",
    )
    location: Optional[str] = Field(None, description="Location name if available")


class DaySchema(BaseModel):
    date: datetime.date = Field(..., description="The date for this day of the itinerary")
    activities: List[ActivitySchema] = Field(
        default_factory=list,
        description="List of activities planned for this day",
    )


class ItinerarySchema(BaseModel):
    trip_summary: str = Field(
        ...,
        description="A brief summary/overview of the trip itinerary",
    )
    days: List[DaySchema] = Field(
        ...,
        description="Chronological list of days with their activities",
    )
