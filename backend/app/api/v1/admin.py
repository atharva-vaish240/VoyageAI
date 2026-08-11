"""Admin-only endpoints for trip management."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.admin import (
    AdminTripResponse,
    AdminTripDetailResponse,
    AdminTripUpdate,
)
from app.services import admin_service

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)


@router.get("/test")
def admin_test(current_user: User = Depends(require_role(UserRole.ADMIN))):
    """Test endpoint — accessible only to ADMIN users."""
    return {
        "message": "Admin access granted.",
        "admin_id": current_user.id,
        "admin_email": current_user.email,
    }


@router.get(
    "/trips",
    response_model=list[AdminTripResponse],
    summary="List all trips across all users (Admin only)",
)
def list_all_trips(db: Session = Depends(get_db)):
    """Retrieve lightweight trip list across all users."""
    return admin_service.list_all_trips_admin(db)


@router.get(
    "/trips/{trip_id}",
    response_model=AdminTripDetailResponse,
    summary="Get trip details by ID across any user (Admin only)",
)
def get_trip(trip_id: int, db: Session = Depends(get_db)):
    """Retrieve full trip details for any user."""
    return admin_service.get_trip_admin(db, trip_id)


@router.patch(
    "/trips/{trip_id}",
    response_model=AdminTripDetailResponse,
    summary="Update trip metadata by ID (Admin only)",
)
def update_trip(
    trip_id: int,
    data: AdminTripUpdate,
    db: Session = Depends(get_db),
):
    """Update editable trip metadata fields ONLY.
    
    Does NOT modify or regenerate itinerary or destination_image.
    """
    return admin_service.update_trip_admin(db, trip_id, data)


@router.delete(
    "/trips/{trip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete any trip by ID (Admin only)",
)
def delete_trip(trip_id: int, db: Session = Depends(get_db)):
    """Permanently delete a trip across any user."""
    admin_service.delete_trip_admin(db, trip_id)
