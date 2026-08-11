"""Tests for the Trip database model and Pydantic schemas."""

from datetime import date, timedelta
import pytest
from pydantic import ValidationError

from app.core.database import SessionLocal
from app.models.user import User
from app.models.trip import Trip, TripStatus
from app.schemas.trip import TripCreate, TripUpdate


def _create_test_user(email: str) -> User:
    """Helper to create a test user directly in DB."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                name="Trip Test User",
                email=email,
                password_hash="somehash123",
                role="USER",
                auth_provider="local",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    finally:
        db.close()


def _cleanup_user(email: str):
    """Cleanup test user and all cascade data."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.query(Trip).filter(Trip.user_id == user.id).delete()
            db.delete(user)
            db.commit()
    finally:
        db.close()


# ── 1. Schema Validation Tests ─────────────────────────────────────────

def test_trip_create_schema_valid():
    start = date.today()
    end = start + timedelta(days=5)
    schema = TripCreate(
        title="Paris Getaway",
        destination="Paris",
        start_date=start,
        end_date=end,
        status="PLANNED",
    )
    assert schema.title == "Paris Getaway"
    assert schema.status == TripStatus.PLANNED


def test_trip_create_schema_invalid_dates_rejected():
    start = date.today()
    end = start - timedelta(days=1)  # end before start
    with pytest.raises(ValidationError):
        TripCreate(
            title="Invalid Dates",
            start_date=start,
            end_date=end,
        )


def test_trip_update_schema_invalid_dates_rejected():
    start = date.today()
    end = start - timedelta(days=1)
    with pytest.raises(ValidationError):
        TripUpdate(
            start_date=start,
            end_date=end,
        )


# ── 2. Model Insertion & Field Verification ───────────────────────────

def test_trip_model_persistence():
    email = "t_persist@test.com"
    _cleanup_user(email)
    user = _create_test_user(email)

    db = SessionLocal()
    try:
        start = date.today()
        end = start + timedelta(days=7)
        trip = Trip(
            user_id=user.id,
            title="Summer Vacation",
            destination="Rome",
            start_date=start,
            end_date=end,
            status=TripStatus.PLANNED,
        )
        db.add(trip)
        db.commit()
        db.refresh(trip)

        # Retrieve and verify
        db_trip = db.query(Trip).filter(Trip.id == trip.id).first()
        assert db_trip is not None
        assert db_trip.title == "Summer Vacation"
        assert db_trip.destination == "Rome"
        assert db_trip.status == TripStatus.PLANNED
        assert db_trip.user_id == user.id
        assert db_trip.created_at is not None
        assert db_trip.updated_at is not None
    finally:
        db.close()
        _cleanup_user(email)


# ── 3. Relationship & Cascade Delete ──────────────────────────────────

def test_trip_cascade_delete():
    email = "t_cascade@test.com"
    _cleanup_user(email)
    user = _create_test_user(email)

    db = SessionLocal()
    try:
        # Create a trip
        trip = Trip(
            user_id=user.id,
            title="Brief Voyage",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
            status=TripStatus.DRAFT,
        )
        db.add(trip)
        db.commit()
        trip_id = trip.id

        # Verify trip exists
        assert db.query(Trip).filter(Trip.id == trip_id).first() is not None

        # Delete user
        db_user = db.query(User).filter(User.id == user.id).first()
        db.delete(db_user)
        db.commit()

        # Verify trip is cascade deleted
        assert db.query(Trip).filter(Trip.id == trip_id).first() is None
    finally:
        db.close()
        _cleanup_user(email)
