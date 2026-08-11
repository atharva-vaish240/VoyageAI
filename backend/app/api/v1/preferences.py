"""User travel preferences endpoints.

GET  /api/v1/preferences     — retrieve current user's preferences
PUT  /api/v1/preferences     — create or fully replace preferences
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.preference import UserPreference
from app.schemas.preference import PreferencesUpdate, PreferencesResponse

router = APIRouter(prefix="/preferences", tags=["Preferences"])


def _pref_to_response(pref: UserPreference) -> PreferencesResponse:
    """Convert DB model to response, splitting interests string into list."""
    return PreferencesResponse(
        id=pref.id,
        user_id=pref.user_id,
        food_preference=pref.food_preference,
        drinking_preference=pref.drinking_preference,
        travel_style=pref.travel_style,
        travel_pace=pref.travel_pace,
        accommodation_preference=pref.accommodation_preference,
        interests=[i.strip() for i in pref.interests.split(",") if i.strip()] if pref.interests else [],
        additional_preferences=pref.additional_preferences,
        created_at=pref.created_at,
        updated_at=pref.updated_at,
    )


@router.get("", response_model=PreferencesResponse)
def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current user's travel preferences. Creates defaults if none exist."""
    pref = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()
    if not pref:
        # Auto-create default preferences
        pref = UserPreference(user_id=current_user.id)
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return _pref_to_response(pref)


@router.put("", response_model=PreferencesResponse)
def update_preferences(
    data: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or fully replace the current user's travel preferences."""
    pref = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()

    if not pref:
        pref = UserPreference(user_id=current_user.id)
        db.add(pref)

    # Set attributes
    pref.food_preference = data.food_preference
    pref.drinking_preference = data.drinking_preference
    pref.travel_style = data.travel_style
    pref.travel_pace = data.travel_pace
    pref.accommodation_preference = data.accommodation_preference
    pref.interests = ",".join(data.interests)
    pref.additional_preferences = data.additional_preferences

    db.commit()
    db.refresh(pref)
    return _pref_to_response(pref)
