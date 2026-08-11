"""Trip CRUD endpoints + AI itinerary generation + Google Calendar scheduling."""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.preference import UserPreference
from app.schemas.trip import TripCreate, TripUpdate, TripResponse, TripDetailResponse
from app.schemas.itinerary import ItinerarySchema
from app.schemas.calendar import TripCalendarResponse
from app.services.trip_service import (
    TripError,
    create_trip,
    list_user_trips,
    get_user_trip,
    update_trip,
    delete_trip,
)
from app.services.ai_service import generate_itinerary, AIServiceError
from app.services.google_calendar_service import (
    GoogleCalendarError,
    schedule_trip_itinerary_to_calendar,
)

router = APIRouter(prefix="/trips", tags=["Trips"])


@router.post("", response_model=TripResponse, status_code=201)
def create_trip_route(
    body: TripCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a trip for the authenticated user."""
    try:
        return create_trip(db, current_user.id, body)
    except TripError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.get("", response_model=list[TripResponse])
def list_trips_route(
    status: str = "all",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all trips belonging to the authenticated user, optionally filtered by status (lightweight)."""
    return list_user_trips(db, current_user.id, status=status)


@router.get("/{trip_id}", response_model=TripDetailResponse)
def get_trip_route(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve a single trip belonging to the authenticated user, including planning info and itinerary."""
    try:
        return get_user_trip(db, current_user.id, trip_id)
    except TripError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.patch("/{trip_id}", response_model=TripDetailResponse)
def update_trip_route(
    trip_id: int,
    body: TripUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a trip belonging to the authenticated user."""
    try:
        return update_trip(db, current_user.id, trip_id, body)
    except TripError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete("/{trip_id}", status_code=204)
def delete_trip_route(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a trip belonging to the authenticated user."""
    try:
        delete_trip(db, current_user.id, trip_id)
    except TripError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return Response(status_code=204)


@router.post("/{trip_id}/generate-itinerary", response_model=ItinerarySchema)
def generate_itinerary_route(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate an AI-powered itinerary for the given trip and persist it in PostgreSQL.

    The trip must belong to the authenticated user.
    """
    try:
        trip = get_user_trip(db, current_user.id, trip_id)
    except TripError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    if not trip.destination:
        raise HTTPException(
            status_code=400,
            detail="Trip destination must be set before generating an itinerary.",
        )

    preferences = (
        db.query(UserPreference)
        .filter(UserPreference.user_id == current_user.id)
        .first()
    )

    try:
        itinerary = generate_itinerary(
            destination=trip.destination,
            start_date=trip.start_date,
            end_date=trip.end_date,
            preferences=preferences,
            num_travellers=trip.num_travellers,
            budget=trip.budget,
            special_requirements=trip.special_requirements,
        )
        trip.itinerary = itinerary.model_dump(mode="json")
        db.commit()
        return itinerary
    except AIServiceError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/{trip_id}/calendar", response_model=TripCalendarResponse)
def schedule_trip_calendar_route(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Schedule the itinerary of a user's trip into their primary Google Calendar.

    Enforces trip ownership (returns 404 if not found/unauthorized).
    Requires a valid connected Google Calendar for the user.
    """
    try:
        trip = get_user_trip(db, current_user.id, trip_id)
    except TripError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    try:
        return schedule_trip_itinerary_to_calendar(db, current_user.id, trip)
    except GoogleCalendarError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
