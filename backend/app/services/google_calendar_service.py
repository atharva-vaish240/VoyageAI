"""Service for Google Calendar OAuth integration, connection persistence, and itinerary scheduling."""

import hashlib
import re
from datetime import datetime, date, time, timedelta, timezone
from urllib.parse import urlencode
import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import encrypt_token, decrypt_token
from app.models.google_calendar import GoogleCalendarConnection
from app.schemas.itinerary import ItinerarySchema
from app.schemas.calendar import TripCalendarResponse, FailedActivityDetail


class GoogleCalendarError(Exception):
    """Custom exception for Google Calendar operations."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
CALENDAR_EVENTS_SCOPE = "https://www.googleapis.com/auth/calendar.events"


def get_google_calendar_auth_url() -> str:
    """Build the Google OAuth 2.0 authorization URL for Google Calendar access."""
    settings = get_settings()

    if not settings.GOOGLE_CLIENT_ID:
        raise GoogleCalendarError(
            status_code=400,
            detail="Google OAuth is not configured in backend settings.",
        )

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": CALENDAR_EVENTS_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{GOOGLE_AUTH_URL}?" + urlencode(params)


def exchange_code_for_tokens(code: str) -> dict:
    """Exchange an OAuth authorization code server-side for Google tokens."""
    settings = get_settings()

    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise GoogleCalendarError(
            status_code=400,
            detail="Google OAuth client credentials are not configured.",
        )

    if not code or not code.strip():
        raise GoogleCalendarError(
            status_code=400,
            detail="Authorization code must be provided.",
        )

    try:
        response = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code.strip(),
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=10.0,
        )
        if response.status_code != 200:
            raise GoogleCalendarError(
                status_code=400,
                detail="Failed to exchange Google authorization code.",
            )

        token_data = response.json()
        if "access_token" not in token_data:
            raise GoogleCalendarError(
                status_code=400,
                detail="Invalid token response from Google OAuth server.",
            )

        return token_data
    except GoogleCalendarError:
        raise
    except Exception:
        raise GoogleCalendarError(
            status_code=400,
            detail="Failed to exchange Google authorization code.",
        )


def save_or_update_google_connection(
    db: Session, user_id: int, token_data: dict
) -> GoogleCalendarConnection:
    """Persist or update encrypted Google OAuth credentials for a specific user."""
    raw_access_token = token_data.get("access_token")
    raw_refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")

    if not raw_access_token:
        raise GoogleCalendarError(status_code=400, detail="Missing access token in payload.")

    encrypted_access = encrypt_token(raw_access_token)
    encrypted_refresh = encrypt_token(raw_refresh_token) if raw_refresh_token else None

    token_expiry = None
    if isinstance(expires_in, (int, float)):
        token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    conn = (
        db.query(GoogleCalendarConnection)
        .filter(GoogleCalendarConnection.user_id == user_id)
        .first()
    )

    if conn:
        conn.access_token = encrypted_access
        if encrypted_refresh:
            conn.refresh_token = encrypted_refresh
        conn.token_expiry = token_expiry
        conn.updated_at = datetime.now(timezone.utc)
    else:
        conn = GoogleCalendarConnection(
            user_id=user_id,
            access_token=encrypted_access,
            refresh_token=encrypted_refresh,
            token_expiry=token_expiry,
        )
        db.add(conn)

    db.commit()
    db.refresh(conn)
    return conn


def get_user_google_connection(db: Session, user_id: int) -> GoogleCalendarConnection | None:
    """Retrieve the Google Calendar connection for a user."""
    return (
        db.query(GoogleCalendarConnection)
        .filter(GoogleCalendarConnection.user_id == user_id)
        .first()
    )


def refresh_google_access_token(db: Session, conn: GoogleCalendarConnection) -> str:
    """Refresh an expired access token using the stored encrypted refresh token."""
    settings = get_settings()

    if not conn.refresh_token:
        raise GoogleCalendarError(
            status_code=400,
            detail="No Google refresh token available. Re-authorization required.",
        )

    decrypted_refresh = decrypt_token(conn.refresh_token)
    if not decrypted_refresh:
        raise GoogleCalendarError(
            status_code=400,
            detail="Invalid stored refresh token. Re-authorization required.",
        )

    try:
        response = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": decrypted_refresh,
                "grant_type": "refresh_token",
            },
            timeout=10.0,
        )
        if response.status_code != 200:
            raise GoogleCalendarError(
                status_code=400,
                detail="Failed to refresh Google Calendar access token.",
            )

        token_data = response.json()
        new_access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3600)

        if not new_access_token:
            raise GoogleCalendarError(
                status_code=400,
                detail="Google token refresh did not return a valid access token.",
            )

        conn.access_token = encrypt_token(new_access_token)
        conn.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        conn.updated_at = datetime.now(timezone.utc)
        db.commit()

        return new_access_token
    except GoogleCalendarError:
        raise
    except Exception:
        raise GoogleCalendarError(
            status_code=400,
            detail="Failed to refresh Google Calendar access token.",
        )


def get_valid_access_token(db: Session, user_id: int) -> str:
    """Return a valid decrypted Google access token for the given user, refreshing if expired."""
    conn = get_user_google_connection(db, user_id)
    if not conn:
        raise GoogleCalendarError(
            status_code=400,
            detail="Google Calendar is not connected. Please connect Google Calendar first.",
        )

    now = datetime.now(timezone.utc)
    if conn.token_expiry and conn.token_expiry <= (now + timedelta(seconds=60)):
        return refresh_google_access_token(db, conn)

    decrypted_access = decrypt_token(conn.access_token)
    if not decrypted_access:
        return refresh_google_access_token(db, conn)

    return decrypted_access


# ── ITINERARY MAPPING & SCHEDULING LOGIC ───────────────────────


def generate_deterministic_event_id(trip_id: int, day_date: str | date, activity_index: int) -> str:
    """Generate a valid lowercase base32hex Google Calendar event ID.

    Constraints: 5-1024 characters, characters 0-9 and a-v.
    """
    date_str = str(day_date)
    seed = f"voyageai_trip_{trip_id}_day_{date_str}_act_{activity_index}"
    hashed = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:30]
    return f"v{hashed}"


def parse_activity_time(date_val: date, approx_time: str, act_index: int) -> tuple[datetime, datetime]:
    """Parse activity approximate_time and day date into start and end datetimes."""
    cleaned = (approx_time or "").strip().lower()

    # 1. Phrases
    if "morning" in cleaned:
        start_t = time(9, 0)
        end_t = time(10, 30)
        return datetime.combine(date_val, start_t), datetime.combine(date_val, end_t)
    elif "afternoon" in cleaned:
        start_t = time(14, 0)
        end_t = time(15, 30)
        return datetime.combine(date_val, start_t), datetime.combine(date_val, end_t)
    elif "evening" in cleaned:
        start_t = time(18, 0)
        end_t = time(19, 30)
        return datetime.combine(date_val, start_t), datetime.combine(date_val, end_t)

    # 2. Explicit clock time regex (e.g., "09:00 AM", "14:30", "2:30 PM", "9am")
    match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', cleaned)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2)) if match.group(2) else 0
        ampm = match.group(3)

        if ampm:
            if ampm == "pm" and hours < 12:
                hours += 12
            elif ampm == "am" and hours == 12:
                hours = 0

        if 0 <= hours <= 23 and 0 <= minutes <= 59:
            start_dt = datetime.combine(date_val, time(hours, minutes))
            end_dt = start_dt + timedelta(hours=1)
            return start_dt, end_dt

    # 3. Sequential 1-hour slots fallback starting at 10:00
    start_hour = (10 + act_index) % 24
    start_dt = datetime.combine(date_val, time(start_hour, 0))
    end_dt = start_dt + timedelta(hours=1)
    return start_dt, end_dt


def create_google_calendar_event(
    access_token: str,
    event_id: str,
    summary: str,
    description: str,
    location: str | None,
    start_dt: datetime,
    end_dt: datetime,
) -> str:
    """Insert an event into the primary Google Calendar via REST API.

    Returns "created" or "already_exists", or raises GoogleCalendarError.
    """
    url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    body = {
        "id": event_id,
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": "UTC",
        },
    }
    if location and location.strip():
        body["location"] = location.strip()

    response = httpx.post(url, headers=headers, json=body, timeout=10.0)

    if response.status_code in (200, 201):
        return "created"
    elif response.status_code == 409:
        return "already_exists"
    else:
        err_msg = f"Google API error ({response.status_code}): {response.text}"
        print(f"[GOOGLE CALENDAR ERROR] {err_msg}")
        raise GoogleCalendarError(
            status_code=response.status_code,
            detail=err_msg,
        )


def schedule_trip_itinerary_to_calendar(
    db: Session, user_id: int, trip
) -> TripCalendarResponse:
    """Schedule all activities in a trip itinerary into the user's primary Google Calendar."""
    access_token = get_valid_access_token(db, user_id)

    if not trip.itinerary:
        raise GoogleCalendarError(
            status_code=400,
            detail="Trip has no generated itinerary to schedule.",
        )

    try:
        itinerary = ItinerarySchema.model_validate(trip.itinerary)
    except Exception:
        raise GoogleCalendarError(
            status_code=400,
            detail="Invalid itinerary data stored for this trip.",
        )

    total = 0
    created = 0
    already_exists = 0
    failed = 0
    failed_activities: list[FailedActivityDetail] = []

    for day in itinerary.days:
        date_val = day.date
        for act_idx, act in enumerate(day.activities):
            total += 1
            event_id = generate_deterministic_event_id(trip.id, date_val, act_idx)
            start_dt, end_dt = parse_activity_time(date_val, act.approximate_time, act_idx)

            try:
                result = create_google_calendar_event(
                    access_token=access_token,
                    event_id=event_id,
                    summary=act.title,
                    description=act.description,
                    location=act.location,
                    start_dt=start_dt,
                    end_dt=end_dt,
                )
                if result == "created":
                    created += 1
                elif result == "already_exists":
                    already_exists += 1
            except Exception as e:
                failed += 1
                safe_err = getattr(e, "detail", "Failed to schedule event")
                failed_activities.append(
                    FailedActivityDetail(
                        day=str(date_val),
                        activity_index=act_idx,
                        title=act.title,
                        error=safe_err,
                    )
                )

    return TripCalendarResponse(
        total_activities=total,
        created=created,
        already_exists=already_exists,
        failed=failed,
        calendar_url="https://calendar.google.com/calendar/u/0/r",
        failed_activities=failed_activities,
    )
