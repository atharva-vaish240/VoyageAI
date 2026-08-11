"""Destination recommendations endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.preference import UserPreference
from app.schemas.recommendation import RecommendationsResponse
from app.services.ai_service import generate_recommendations, AIServiceError

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.post("", response_model=RecommendationsResponse)
def get_recommendations_route(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate 3 AI destination recommendations (Seasonal Pick, Hidden Gem, Experience Pick) for the user."""
    preferences = (
        db.query(UserPreference)
        .filter(UserPreference.user_id == current_user.id)
        .first()
    )

    try:
        return generate_recommendations(preferences=preferences)
    except AIServiceError as e:
        raise HTTPException(status_code=503, detail=str(e))
