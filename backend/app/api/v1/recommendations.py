"""Destination recommendations endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.preference import UserPreference
from app.schemas.recommendation import RecommendationsResponse
from app.services.ai_service import generate_recommendations, AIServiceError
from app.services.pexels_service import search_destination_image

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.post("", response_model=RecommendationsResponse)
def get_recommendations_route(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate 3 AI destination recommendations (Seasonal Pick, Hidden Gem, Experience Pick) enriched with Pexels photos."""
    preferences = (
        db.query(UserPreference)
        .filter(UserPreference.user_id == current_user.id)
        .first()
    )

    try:
        recommendations = generate_recommendations(preferences=preferences)

        # Enrich each pick with a relevant Pexels photo
        for pick in [
            recommendations.seasonal_pick,
            recommendations.hidden_gem,
            recommendations.experience_pick,
        ]:
            if pick.image_search_term:
                pick.image = search_destination_image(pick.image_search_term)

        return recommendations
    except AIServiceError as e:
        raise HTTPException(status_code=503, detail=str(e))
