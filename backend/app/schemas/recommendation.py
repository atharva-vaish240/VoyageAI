"""Pydantic schemas for destination recommendations."""

from typing import List, Optional
from pydantic import BaseModel, Field


class RecommendationImage(BaseModel):
    """Attribution and source URLs for a Pexels photo."""
    url: str = Field(..., description="Image display URL")
    photographer: str = Field(..., description="Name of photographer")
    photographer_url: str = Field(..., description="Link to photographer's Pexels profile")
    pexels_url: str = Field(..., description="Link to original photo on Pexels")


class RecommendationItem(BaseModel):
    """Schema for a single destination recommendation pick."""
    category: str = Field(..., description="Category: Seasonal Pick, Hidden Gem, or Experience Pick")
    destination: str = Field(..., description="Destination name (e.g. Kyoto, Japan)")
    tagline: str = Field(..., description="Catchy short tagline")
    reason: str = Field(..., description="Concise reason for recommendation based on season & preferences")
    highlights: List[str] = Field(..., description="Top 2-3 key highlights or activities")
    image_search_term: str = Field(default="", description="Recognizable landmark or spot for image search (e.g. Dal Lake Kashmir)")
    image: Optional[RecommendationImage] = Field(None, description="Enriched Pexels photo metadata if available")


class RecommendationsResponse(BaseModel):
    """Schema for the 3 structured destination recommendations."""
    seasonal_pick: RecommendationItem
    hidden_gem: RecommendationItem
    experience_pick: RecommendationItem
