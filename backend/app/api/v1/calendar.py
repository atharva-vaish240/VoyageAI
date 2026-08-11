"""Google Calendar API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.calendar import (
    AuthUrlResponse,
    CalendarCallbackRequest,
    CalendarCallbackResponse,
    CalendarStatusResponse,
)
from app.services.google_calendar_service import (
    GoogleCalendarError,
    get_google_calendar_auth_url,
    exchange_code_for_tokens,
    save_or_update_google_connection,
    get_user_google_connection,
)

router = APIRouter(prefix="/calendar", tags=["Google Calendar"])


@router.get("/auth-url", response_model=AuthUrlResponse)
def get_auth_url_route(current_user: User = Depends(get_current_user)):
    """Generate and return Google OAuth authorization URL for Calendar access.

    Requires valid VoyageAI JWT authentication.
    """
    try:
        url = get_google_calendar_auth_url()
        return AuthUrlResponse(auth_url=url)
    except GoogleCalendarError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.post("/callback", response_model=CalendarCallbackResponse)
def calendar_callback_route(
    body: CalendarCallbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Exchange an OAuth authorization code for Google credentials and persist connection for user.

    Requires valid VoyageAI JWT authentication.
    Does NOT return Google access or refresh tokens in the response.
    """
    try:
        token_data = exchange_code_for_tokens(body.code)
        save_or_update_google_connection(db, current_user.id, token_data)
        return CalendarCallbackResponse(
            status="success",
            message="Google Calendar connected successfully.",
        )
    except GoogleCalendarError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.get("/status", response_model=CalendarStatusResponse)
def calendar_status_route(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return whether the current authenticated user has an active Google Calendar connection.

    Requires valid VoyageAI JWT authentication.
    Returns safe boolean only — no token data or secrets exposed.
    """
    conn = get_user_google_connection(db, current_user.id)
    return CalendarStatusResponse(connected=conn is not None)
