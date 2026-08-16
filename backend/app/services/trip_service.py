"""Trip CRUD and collaboration business logic."""

from datetime import date
import logging
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from app.models.trip import Trip
from app.models.trip_member import TripMember, MemberRole
from app.models.user import User
from app.schemas.trip import (
    TripCreate,
    TripUpdate,
    TripResponse,
    TripDetailResponse,
    TripMemberResponse,
)
from app.services.pexels_service import search_destination_image

logger = logging.getLogger(__name__)


class TripError(Exception):
    """Raised when a trip operation fails."""

    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code


def get_accessible_trip(db: Session, user_id: int, trip_id: int) -> tuple[Trip, str]:
    """Retrieve a trip if user is the owner or a member. Returns (trip, role).

    Raises 404 if trip not found or user is not authorized.
    """
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise TripError("Trip not found.", status_code=404)

    if trip.user_id == user_id:
        return trip, "OWNER"

    membership = (
        db.query(TripMember)
        .filter(TripMember.trip_id == trip_id, TripMember.user_id == user_id)
        .first()
    )
    if membership:
        return trip, "MEMBER"

    raise TripError("Trip not found.", status_code=404)


def get_owned_trip(db: Session, user_id: int, trip_id: int) -> Trip:
    """Retrieve a trip only if the user is the owner.

    Raises 404 if trip does not exist or user is not the owner.
    """
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip or trip.user_id != user_id:
        raise TripError("Trip not found.", status_code=404)
    return trip


def get_user_trip(db: Session, user_id: int, trip_id: int, require_owner: bool = False) -> Trip:
    """Return a trip for the given user, optionally requiring ownership."""
    if require_owner:
        trip = get_owned_trip(db, user_id, trip_id)
        trip.role = "OWNER"
        trip.is_owner = True
        return trip

    trip, role = get_accessible_trip(db, user_id, trip_id)
    trip.role = role
    trip.is_owner = (role == "OWNER")
    return trip


def get_trip_detail(db: Session, user_id: int, trip_id: int) -> TripDetailResponse:
    """Return full trip details including member list and user's role."""
    trip, role = get_accessible_trip(db, user_id, trip_id)
    members = list_trip_members(db, user_id, trip_id)
    is_owner = (role == "OWNER")
    return TripDetailResponse(
        id=trip.id,
        user_id=trip.user_id,
        title=trip.title,
        destination=trip.destination,
        start_date=trip.start_date,
        end_date=trip.end_date,
        status=trip.status,
        destination_image=trip.destination_image,
        num_travellers=trip.num_travellers,
        budget=trip.budget,
        special_requirements=trip.special_requirements,
        itinerary=trip.itinerary,
        created_at=trip.created_at,
        updated_at=trip.updated_at,
        role=role,
        is_owner=is_owner,
        members=members,
    )


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
    trip.role = "OWNER"
    trip.is_owner = True
    return trip


def list_user_trips(db: Session, user_id: int, status: str = "all") -> list[TripResponse]:
    """Return trips owned by or shared with the given user, optionally filtered by status (upcoming/past/all)."""
    member_trip_ids = (
        db.query(TripMember.trip_id)
        .filter(TripMember.user_id == user_id)
        .scalar_subquery()
    )

    query = db.query(Trip).filter(
        or_(
            Trip.user_id == user_id,
            Trip.id.in_(member_trip_ids),
        )
    )

    today = date.today()
    if status == "upcoming":
        query = query.filter(Trip.end_date >= today).order_by(Trip.start_date.asc(), Trip.id.asc())
    elif status == "past":
        query = query.filter(Trip.end_date < today).order_by(Trip.start_date.desc(), Trip.id.desc())
    else:
        # Default or "all"
        query = query.order_by(Trip.start_date.desc(), Trip.id.desc())

    trips = query.all()
    results: list[TripResponse] = []
    for t in trips:
        is_owner = (t.user_id == user_id)
        t.role = "OWNER" if is_owner else "MEMBER"
        t.is_owner = is_owner
        results.append(TripResponse.model_validate(t))

    return results


def update_trip(db: Session, user_id: int, trip_id: int, data: TripUpdate) -> Trip:
    """Update a trip belonging to the given user (owner only). Refetches photo if destination changes."""
    trip = get_owned_trip(db, user_id, trip_id)
    updates = data.model_dump(exclude_unset=True)

    if not updates:
        trip.role = "OWNER"
        trip.is_owner = True
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
    trip.role = "OWNER"
    trip.is_owner = True
    return trip


def delete_trip(db: Session, user_id: int, trip_id: int) -> None:
    """Delete a trip belonging to the given user (owner only)."""
    trip = get_owned_trip(db, user_id, trip_id)
    db.delete(trip)
    db.commit()


# ── Collaboration / Member Management ────────────────────────────

def list_trip_members(db: Session, user_id: int, trip_id: int) -> list[TripMemberResponse]:
    """List all collaborators (owner + members) for an accessible trip."""
    trip, _ = get_accessible_trip(db, user_id, trip_id)

    owner_resp = TripMemberResponse(
        id=0,
        trip_id=trip.id,
        user_id=trip.user.id,
        email=trip.user.email,
        name=trip.user.name,
        role="OWNER",
        created_at=trip.created_at,
    )

    memberships = (
        db.query(TripMember)
        .filter(TripMember.trip_id == trip_id)
        .order_by(TripMember.created_at.asc())
        .all()
    )

    member_resps = [
        TripMemberResponse(
            id=m.id,
            trip_id=m.trip_id,
            user_id=m.user.id,
            email=m.user.email,
            name=m.user.name,
            role=m.role.value if hasattr(m.role, "value") else str(m.role),
            created_at=m.created_at,
        )
        for m in memberships
    ]

    return [owner_resp] + member_resps


def add_trip_member(
    db: Session,
    owner_user_id: int,
    trip_id: int,
    email: str,
) -> TripMemberResponse:
    """Add a registered user to a trip by email (owner only)."""
    trip = get_owned_trip(db, owner_user_id, trip_id)

    target_user = (
        db.query(User)
        .filter(func.lower(User.email) == email.strip().lower())
        .first()
    )
    if not target_user:
        raise TripError("User with this email not found.", status_code=404)

    if target_user.id == trip.user_id:
        raise TripError("Cannot add the trip owner as a member.", status_code=400)

    existing_membership = (
        db.query(TripMember)
        .filter(TripMember.trip_id == trip.id, TripMember.user_id == target_user.id)
        .first()
    )
    if existing_membership:
        raise TripError("User is already a member of this trip.", status_code=400)

    member = TripMember(
        trip_id=trip.id,
        user_id=target_user.id,
        role=MemberRole.MEMBER,
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    return TripMemberResponse(
        id=member.id,
        trip_id=trip.id,
        user_id=target_user.id,
        email=target_user.email,
        name=target_user.name,
        role="MEMBER",
        created_at=member.created_at,
    )


def remove_trip_member(
    db: Session,
    owner_user_id: int,
    trip_id: int,
    target_user_id: int,
) -> None:
    """Remove a member from a trip (owner only)."""
    trip = get_owned_trip(db, owner_user_id, trip_id)

    if target_user_id == trip.user_id:
        raise TripError("Cannot remove the trip owner.", status_code=400)

    membership = (
        db.query(TripMember)
        .filter(TripMember.trip_id == trip.id, TripMember.user_id == target_user_id)
        .first()
    )
    if not membership:
        raise TripError("Member not found in this trip.", status_code=404)

    db.delete(membership)
    db.commit()


def _validate_date_range(start_date: date, end_date: date) -> None:
    if end_date < start_date:
        raise TripError(
            "end_date cannot be before start_date",
            status_code=422,
        )
