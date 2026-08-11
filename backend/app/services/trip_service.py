"""Trip CRUD business logic."""

from datetime import date
import logging
from sqlalchemy.orm import Session

from app.models.trip import Trip
from app.schemas.trip import TripCreate, TripUpdate
from app.services.pexels_service import search_destination_image

logger = logging.getLogger(__name__)


class TripError(Exception):
    """Raised when a trip operation fails."""

    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code


def create_trip(db: Session, user_id: int, data: TripCreate) -> Trip:
    """Create a trip owned by the given user.

    If destination_image is already provided (e.g. passed from Home recommendation pick),
    persist it directly without querying Pexels.
    Otherwise, if destination is present, search Pexels for a representative photo.
    """
    image_data = None
    if data.destination_image:
        image_data = data.destination_image.model_dump(mode="json")
    elif data.destination and data.destination.strip():
        try:
            image_obj = search_destination_image(data.destination.strip())
            if image_obj:
                image_data = image_obj.model_dump(mode="json")
        except Exception as e:
            logger.warning(f"Pexels fetch failed during trip creation: {e}")

    trip = Trip(
        user_id=user_id,
        title=data.title,
        destination=data.destination,
        start_date=data.start_date,
        end_date=data.end_date,
        status=data.status,
        num_travellers=data.num_travellers,
        budget=data.budget,
        special_requirements=data.special_requirements,
        destination_image=image_data,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


def list_user_trips(db: Session, user_id: int, status: str = "all") -> list[Trip]:
    """Return trips belonging to the given user, optionally filtered by status (upcoming/past/all)."""
    query = db.query(Trip).filter(Trip.user_id == user_id)

    today = date.today()
    if status == "upcoming":
        query = query.filter(Trip.end_date >= today).order_by(Trip.start_date.asc(), Trip.id.asc())
    elif status == "past":
        query = query.filter(Trip.end_date < today).order_by(Trip.start_date.desc(), Trip.id.desc())
    else:
        # Default or "all"
        query = query.order_by(Trip.start_date.desc(), Trip.id.desc())

    return query.all()


def get_user_trip(db: Session, user_id: int, trip_id: int) -> Trip:
    """Return a single trip if it belongs to the user, else raise 404."""
    trip = (
        db.query(Trip)
        .filter(Trip.id == trip_id, Trip.user_id == user_id)
        .first()
    )
    if not trip:
        raise TripError("Trip not found.", status_code=404)
    return trip


def update_trip(db: Session, user_id: int, trip_id: int, data: TripUpdate) -> Trip:
    """Update a trip belonging to the given user. Refetches photo if destination changes."""
    trip = get_user_trip(db, user_id, trip_id)
    updates = data.model_dump(exclude_unset=True)

    if not updates:
        return trip

    destination_changed = "destination" in updates and updates["destination"] != trip.destination

    for field, value in updates.items():
        setattr(trip, field, value)

    _validate_date_range(trip.start_date, trip.end_date)

    if destination_changed:
        if "destination_image" in updates and updates["destination_image"]:
            trip.destination_image = updates["destination_image"].model_dump(mode="json")
        elif trip.destination and trip.destination.strip():
            try:
                image_obj = search_destination_image(trip.destination.strip())
                trip.destination_image = image_obj.model_dump(mode="json") if image_obj else None
            except Exception as e:
                logger.warning(f"Pexels fetch failed during trip update: {e}")
                trip.destination_image = None
        else:
            trip.destination_image = None

    db.commit()
    db.refresh(trip)
    return trip


def delete_trip(db: Session, user_id: int, trip_id: int) -> None:
    """Delete a trip belonging to the given user."""
    trip = get_user_trip(db, user_id, trip_id)
    db.delete(trip)
    db.commit()


def _validate_date_range(start_date: date, end_date: date) -> None:
    if end_date < start_date:
        raise TripError(
            "end_date cannot be before start_date",
            status_code=422,
        )
