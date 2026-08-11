"""Pydantic schemas for Google Calendar API endpoints."""

from typing import List
from pydantic import BaseModel, Field


class AuthUrlResponse(BaseModel):
    auth_url: str = Field(..., description="Google OAuth authorization URL for Calendar access")


class CalendarCallbackRequest(BaseModel):
    code: str = Field(..., description="Google OAuth authorization code")


class CalendarCallbackResponse(BaseModel):
    status: str = Field("success", description="Status of calendar authorization")
    message: str = Field(..., description="Human-readable result message")


class CalendarStatusResponse(BaseModel):
    connected: bool = Field(..., description="Whether Google Calendar is connected for the current user")


class FailedActivityDetail(BaseModel):
    day: str = Field(..., description="Date of the activity")
    activity_index: int = Field(..., description="Index of activity within the day")
    title: str = Field(..., description="Title of the failed activity")
    error: str = Field(..., description="Safe non-sensitive failure reason")


class TripCalendarResponse(BaseModel):
    total_activities: int = Field(..., description="Total activities processed")
    created: int = Field(..., description="Number of new events created in Google Calendar")
    already_exists: int = Field(..., description="Number of events already existing in Google Calendar")
    failed: int = Field(..., description="Number of events that failed to schedule")
    calendar_url: str = Field(
        default="https://calendar.google.com/calendar/u/0/r",
        description="Link to open Google Calendar",
    )
    failed_activities: List[FailedActivityDetail] = Field(
        default_factory=list,
        description="Details of any activities that failed",
    )
