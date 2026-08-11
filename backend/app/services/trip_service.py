"""Trip CRUD business logic."""

from datetime import date

from sqlalchemy.orm import Session

from app.models.trip import Trip
from app.schemas.trip import TripCreate, TripUpdate


class TripError(Exception):
    """Raised when a trip operation fails."""

    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code


def create_trip(db: Session, user_id: int, data: TripCreate) -> Trip:
    """Create a trip owned by the given user."""
    trip = Trip(
        user_id=user_id,
        title=data.title,
        destination=data.destination,
        start_date=data.start_date,
        end_date=data.end_date,
        status=data.status,
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
    """Update a trip belonging to the given user."""
    trip = get_user_trip(db, user_id, trip_id)
    updates = data.model_dump(exclude_unset=True)

    if not updates:
        return trip

    for field, value in updates.items():
        setattr(trip, field, value)

    _validate_date_range(trip.start_date, trip.end_date)
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
