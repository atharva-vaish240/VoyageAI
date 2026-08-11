"""Trip CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.trip import TripCreate, TripUpdate, TripResponse
from app.services.trip_service import (
    TripError,
    create_trip,
    list_user_trips,
    get_user_trip,
    update_trip,
    delete_trip,
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
    """List all trips belonging to the authenticated user, optionally filtered by status."""
    return list_user_trips(db, current_user.id, status=status)


@router.get("/{trip_id}", response_model=TripResponse)
def get_trip_route(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve a single trip belonging to the authenticated user."""
    try:
        return get_user_trip(db, current_user.id, trip_id)
    except TripError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.patch("/{trip_id}", response_model=TripResponse)
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
