"""Pydantic schemas for destination recommendations."""

from typing import List
from pydantic import BaseModel, Field


class RecommendationItem(BaseModel):
    """Schema for a single destination recommendation pick."""
    category: str = Field(..., description="Category: Seasonal Pick, Hidden Gem, or Experience Pick")
    destination: str = Field(..., description="Destination name (e.g. Kyoto, Japan)")
    tagline: str = Field(..., description="Catchy short tagline")
    reason: str = Field(..., description="Concise reason for recommendation based on season & preferences")
    highlights: List[str] = Field(..., description="Top 2-3 key highlights or activities")


class RecommendationsResponse(BaseModel):
    """Schema for the 3 structured destination recommendations."""
    seasonal_pick: RecommendationItem
    hidden_gem: RecommendationItem
    experience_pick: RecommendationItem
