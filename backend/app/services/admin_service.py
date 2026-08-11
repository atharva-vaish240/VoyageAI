"""Admin business logic for trip management."""

import logging
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.models.trip import Trip
from app.schemas.admin import AdminTripUpdate

logger = logging.getLogger(__name__)


def list_all_trips_admin(db: Session) -> list[Trip]:
    """Retrieve all trips belonging to all users for admin management."""
    return (
        db.query(Trip)
        .options(joinedload(Trip.user))
        .order_by(Trip.created_at.desc(), Trip.id.desc())
        .all()
    )


def get_trip_admin(db: Session, trip_id: int) -> Trip:
    """Retrieve a single trip by ID across any user."""
    trip = (
        db.query(Trip)
        .options(joinedload(Trip.user))
        .filter(Trip.id == trip_id)
        .first()
    )
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found.",
        )
    return trip


def update_trip_admin(db: Session, trip_id: int, data: AdminTripUpdate) -> Trip:
    """Update metadata of any user's trip.
    
    IMPORTANT: Metadata fields ONLY.
    Does NOT modify or regenerate itinerary or destination_image.
    """
    trip = get_trip_admin(db, trip_id)
    updates = data.model_dump(exclude_unset=True)

    if not updates:
        return trip

    for field, value in updates.items():
        setattr(trip, field, value)

    if trip.end_date < trip.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date cannot be before start_date",
        )

    db.commit()
    db.refresh(trip)
    return trip


def delete_trip_admin(db: Session, trip_id: int) -> None:
    """Permanently delete a trip belonging to any user."""
    trip = get_trip_admin(db, trip_id)
    db.delete(trip)
    db.commit()
