"""Trip CRUD endpoints + Collaboration / Members + AI itinerary generation + Google Calendar scheduling."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.preference import UserPreference
from app.schemas.trip import (
    TripCreate,
    TripUpdate,
    TripResponse,
    TripDetailResponse,
    TripMemberResponse,
    AddTripMemberRequest,
)
from app.schemas.itinerary import ItinerarySchema
from app.schemas.calendar import TripCalendarResponse
from app.services.trip_service import (
    TripError,
    create_trip,
    list_user_trips,
    get_user_trip,
    get_trip_detail,
    update_trip,
    delete_trip,
    list_trip_members,
    add_trip_member,
    remove_trip_member,
)
from app.services.ai_service import generate_itinerary, AIServiceError
from app.services.google_calendar_service import (
    GoogleCalendarError,
    schedule_trip_itinerary_to_calendar,
)

router = APIRouter(prefix="/trips", tags=["Trips"])


@router.post("", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
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
    """List all trips owned by or shared with the authenticated user, optionally filtered by status."""
    return list_user_trips(db, current_user.id, status=status)


@router.get("/{trip_id}", response_model=TripDetailResponse)
def get_trip_route(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve a single trip (owned or shared), including planning info, itinerary, and member list."""
    try:
        return get_trip_detail(db, current_user.id, trip_id)
    except TripError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.patch("/{trip_id}", response_model=TripDetailResponse)
def update_trip_route(
    trip_id: int,
    body: TripUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update trip metadata (owner only)."""
    try:
        update_trip(db, current_user.id, trip_id, body)
        return get_trip_detail(db, current_user.id, trip_id)
    except TripError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip_route(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a trip (owner only)."""
    try:
        delete_trip(db, current_user.id, trip_id)
    except TripError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Trip Collaboration / Members Endpoints ───────────────────────

@router.post(
    "/{trip_id}/members",
    response_model=TripMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a registered user to a trip (owner only)",
)
def add_member_route(
    trip_id: int,
    body: AddTripMemberRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a registered user to the trip by email (owner only)."""
    try:
        return add_trip_member(db, current_user.id, trip_id, body.email)
    except TripError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.get(
    "/{trip_id}/members",
    response_model=list[TripMemberResponse],
    summary="List all collaborators of a trip (owner and members)",
)
def list_members_route(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve the member list for the trip (accessible to owner and members)."""
    try:
        return list_trip_members(db, current_user.id, trip_id)
    except TripError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete(
    "/{trip_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member from a trip (owner only)",
)
def remove_member_route(
    trip_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a member from the trip (owner only). Cannot remove the trip owner."""
    try:
        remove_trip_member(db, current_user.id, trip_id, user_id)
    except TripError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Itinerary Endpoints (Shared with members) ────────────────────

@router.post("/{trip_id}/generate-itinerary", response_model=ItinerarySchema)
def generate_itinerary_route(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate an AI-powered itinerary for the given trip and persist it in PostgreSQL.

    Owner only.
    """
    try:
        trip = get_user_trip(db, current_user.id, trip_id, require_owner=True)
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


@router.get("/{trip_id}/itinerary", response_model=ItinerarySchema)
def get_trip_itinerary_route(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve the persisted itinerary for the given trip.

    Accessible to owner and members.
    """
    try:
        trip = get_user_trip(db, current_user.id, trip_id)
    except TripError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    if not trip.itinerary:
        raise HTTPException(
            status_code=404,
            detail="Itinerary not found for this trip.",
        )

    return ItinerarySchema.model_validate(trip.itinerary)


@router.put("/{trip_id}/itinerary", response_model=ItinerarySchema)
def update_trip_itinerary_route(
    trip_id: int,
    body: ItinerarySchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update / replace the persisted itinerary for the given trip.

    Accessible to owner and members.
    Updates the canonical PostgreSQL database copy.
    """
    try:
        trip = get_user_trip(db, current_user.id, trip_id)
    except TripError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    trip.itinerary = body.model_dump(mode="json")
    db.commit()
    db.refresh(trip)

    return ItinerarySchema.model_validate(trip.itinerary)


@router.post("/{trip_id}/calendar", response_model=TripCalendarResponse)
def schedule_trip_calendar_route(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Schedule the itinerary of a user's trip into their primary Google Calendar.

    Accessible to owner and members.
    Requires a valid connected Google Calendar for the calling user.
    """
    try:
        trip = get_user_trip(db, current_user.id, trip_id)
    except TripError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    try:
        return schedule_trip_itinerary_to_calendar(db, current_user.id, trip)
    except GoogleCalendarError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
