"""Unit tests for Google Calendar OAuth backend integration, persistence, and itinerary scheduling."""

from datetime import datetime, date, timedelta, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User, RefreshToken
from app.models.trip import Trip, TripStatus
from app.models.google_calendar import GoogleCalendarConnection
from app.services.google_calendar_service import (
    get_valid_access_token,
    generate_deterministic_event_id,
    parse_activity_time,
    GoogleCalendarError,
)

client = TestClient(app)


def get_auth_header(email="cal_test_user@example.com"):
    """Helper to create a test user and return a Bearer authorization header + user ID."""
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == email).first()
        if u:
            db.query(Trip).filter(Trip.user_id == u.id).delete()
            db.query(GoogleCalendarConnection).filter(GoogleCalendarConnection.user_id == u.id).delete()
            db.query(RefreshToken).filter(RefreshToken.user_id == u.id).delete()
            db.delete(u)
            db.commit()
    finally:
        db.close()

    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"name": "Calendar Tester", "email": email, "password": "Password123!"},
    )
    assert signup_res.status_code == 201
    user_id = signup_res.json()["id"]

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, user_id


def setup_test_trip(user_id: int, with_itinerary: bool = True) -> int:
    """Helper to seed a trip with a persisted itinerary for testing."""
    db = SessionLocal()
    try:
        itinerary = None
        if with_itinerary:
            itinerary = {
                "trip_summary": "Awesome Kashmir Tour",
                "days": [
                    {
                        "date": "2026-09-01",
                        "activities": [
                            {
                                "title": "Arrive in Srinagar",
                                "description": "Check in to luxury houseboat",
                                "approximate_time": "09:00 AM",
                                "location": "Dal Lake, Srinagar",
                            },
                            {
                                "title": "Shikara Ride",
                                "description": "Sunset ride on Dal Lake",
                                "approximate_time": "Evening",
                                "location": "Dal Lake",
                            },
                        ],
                    },
                    {
                        "date": "2026-09-02",
                        "activities": [
                            {
                                "title": "Gulmarg Day Trip",
                                "description": "Gondola cable car ride",
                                "approximate_time": "Morning",
                                "location": "Gulmarg",
                            },
                            {
                                "title": "Unknown Time Activity",
                                "description": "Explore local bazaar",
                                "approximate_time": "sometime",
                                "location": "Market",
                            },
                        ],
                    },
                ],
            }

        trip = Trip(
            user_id=user_id,
            title="Kashmir Adventure",
            destination="Srinagar, India",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 3),
            status=TripStatus.PLANNED,
            itinerary=itinerary,
        )
        db.add(trip)
        db.commit()
        db.refresh(trip)
        return trip.id
    finally:
        db.close()


def connect_user_google_calendar(user_id: int):
    """Helper to mock-connect Google Calendar for a test user in DB."""
    db = SessionLocal()
    try:
        from app.core.security import encrypt_token

        conn = GoogleCalendarConnection(
            user_id=user_id,
            access_token=encrypt_token("valid_access_token_abc"),
            refresh_token=encrypt_token("valid_refresh_token_xyz"),
            token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(conn)
        db.commit()
    finally:
        db.close()


class TestGoogleCalendarAuthUrl:
    """Test suite for GET /api/v1/calendar/auth-url."""

    def test_unauthenticated_request_rejected(self):
        res = client.get("/api/v1/calendar/auth-url")
        assert res.status_code == 401

    def test_authenticated_request_returns_valid_url(self):
        headers, _ = get_auth_header("cal_url_test@example.com")
        with patch("app.services.google_calendar_service.get_settings") as mock_settings:
            mock_settings.return_value.GOOGLE_CLIENT_ID = "mock_client_id_123.apps.googleusercontent.com"
            mock_settings.return_value.GOOGLE_CLIENT_SECRET = "mock_secret_abc"
            mock_settings.return_value.GOOGLE_REDIRECT_URI = "http://localhost:5173/auth/google/callback"

            res = client.get("/api/v1/calendar/auth-url", headers=headers)
            assert res.status_code == 200
            data = res.json()

            assert "auth_url" in data
            auth_url = data["auth_url"]
            assert "accounts.google.com" in auth_url
            assert "mock_client_id_123" in auth_url
            assert "calendar.events" in auth_url
            assert "mock_secret_abc" not in auth_url


class TestGoogleCalendarConnectionPersistence:
    """Test suite for OAuth callback connection persistence & status."""

    def test_status_unconnected(self):
        headers, _ = get_auth_header("cal_status_unconnected@example.com")
        res = client.get("/api/v1/calendar/status", headers=headers)
        assert res.status_code == 200
        assert res.json() == {"connected": False}

    def test_callback_creates_connection(self):
        headers, user_id = get_auth_header("cal_conn_create@example.com")

        mock_httpx_resp = MagicMock()
        mock_httpx_resp.status_code = 200
        mock_httpx_resp.json.return_value = {
            "access_token": "secret_access_token_111",
            "refresh_token": "secret_refresh_token_222",
            "expires_in": 3600,
        }

        with patch("httpx.post", return_value=mock_httpx_resp), patch(
            "app.services.google_calendar_service.get_settings"
        ) as mock_settings:
            mock_settings.return_value.GOOGLE_CLIENT_ID = "mock_client_id"
            mock_settings.return_value.GOOGLE_CLIENT_SECRET = "mock_client_secret"
            mock_settings.return_value.GOOGLE_REDIRECT_URI = "http://localhost:5173/auth/google/callback"

            res = client.post(
                "/api/v1/calendar/callback",
                json={"code": "valid_code_123"},
                headers=headers,
            )
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "success"
            assert "connected successfully" in data["message"]

            assert "access_token" not in data
            assert "refresh_token" not in data

        db = SessionLocal()
        try:
            conn = (
                db.query(GoogleCalendarConnection)
                .filter(GoogleCalendarConnection.user_id == user_id)
                .first()
            )
            assert conn is not None
            assert conn.access_token != "secret_access_token_111"
        finally:
            db.close()

        res_status = client.get("/api/v1/calendar/status", headers=headers)
        assert res_status.status_code == 200
        assert res_status.json() == {"connected": True}


class TestUserIsolation:
    """Test suite ensuring strict user isolation for calendar connections."""

    def test_user_a_and_user_b_isolation(self):
        headers_a, user_a_id = get_auth_header("user_a@example.com")
        headers_b, user_b_id = get_auth_header("user_b@example.com")

        mock_httpx_resp = MagicMock()
        mock_httpx_resp.status_code = 200
        mock_httpx_resp.json.return_value = {
            "access_token": "user_a_secret_token",
            "expires_in": 3600,
        }

        with patch("httpx.post", return_value=mock_httpx_resp), patch(
            "app.services.google_calendar_service.get_settings"
        ) as mock_settings:
            mock_settings.return_value.GOOGLE_CLIENT_ID = "mock_client_id"
            mock_settings.return_value.GOOGLE_CLIENT_SECRET = "mock_client_secret"
            mock_settings.return_value.GOOGLE_REDIRECT_URI = "http://localhost:5173/auth/google/callback"

            client.post("/api/v1/calendar/callback", json={"code": "code_a"}, headers=headers_a)

        res_a = client.get("/api/v1/calendar/status", headers=headers_a)
        assert res_a.json()["connected"] is True

        res_b = client.get("/api/v1/calendar/status", headers=headers_b)
        assert res_b.json()["connected"] is False


class TestItineraryCalendarMapping:
    """Test suite for deterministic ID generation & time parsing functions."""

    def test_deterministic_event_id_format_and_stability(self):
        id1 = generate_deterministic_event_id(10, "2026-09-01", 0)
        id2 = generate_deterministic_event_id(10, "2026-09-01", 0)
        id3 = generate_deterministic_event_id(10, "2026-09-01", 1)

        assert id1 == id2  # Fully deterministic
        assert id1 != id3  # Distinct per activity
        assert id1.startswith("v")
        # Validate base32hex lowercase character set (0-9, a-v)
        assert all(c in "0123456789abcdefghijklmnopqrstuv" for c in id1)

    def test_time_parsing_explicit_clock(self):
        date_val = date(2026, 9, 1)
        start, end = parse_activity_time(date_val, "09:00 AM", 0)
        assert start == datetime(2026, 9, 1, 9, 0)
        assert end == datetime(2026, 9, 1, 10, 0)

    def test_time_parsing_phrases(self):
        date_val = date(2026, 9, 1)
        start_m, end_m = parse_activity_time(date_val, "Morning", 0)
        assert start_m == datetime(2026, 9, 1, 9, 0)
        assert end_m == datetime(2026, 9, 1, 10, 30)

        start_a, end_a = parse_activity_time(date_val, "afternoon", 0)
        assert start_a == datetime(2026, 9, 1, 14, 0)
        assert end_a == datetime(2026, 9, 1, 15, 30)

        start_e, end_e = parse_activity_time(date_val, "EVENING", 0)
        assert start_e == datetime(2026, 9, 1, 18, 0)
        assert end_e == datetime(2026, 9, 1, 19, 30)

    def test_time_parsing_fallback(self):
        date_val = date(2026, 9, 1)
        start, end = parse_activity_time(date_val, "unparseable_string", 0)
        assert start == datetime(2026, 9, 1, 10, 0)
        assert end == datetime(2026, 9, 1, 11, 0)

        start2, end2 = parse_activity_time(date_val, "unparseable_string", 1)
        assert start2 == datetime(2026, 9, 1, 11, 0)
        assert end2 == datetime(2026, 9, 1, 12, 0)


class TestTripCalendarScheduling:
    """Test suite for POST /api/v1/trips/{trip_id}/calendar."""

    def test_unauthenticated_scheduling_rejected(self):
        res = client.post("/api/v1/trips/1/calendar")
        assert res.status_code == 401

    def test_scheduling_other_user_trip_returns_404(self):
        headers_a, user_a_id = get_auth_header("user_owner@example.com")
        headers_b, user_b_id = get_auth_header("user_attacker@example.com")
        trip_id = setup_test_trip(user_a_id)

        connect_user_google_calendar(user_b_id)

        res = client.post(f"/api/v1/trips/{trip_id}/calendar", headers=headers_b)
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    def test_missing_google_calendar_connection_returns_400(self):
        headers, user_id = get_auth_header("user_unconnected@example.com")
        trip_id = setup_test_trip(user_id)

        res = client.post(f"/api/v1/trips/{trip_id}/calendar", headers=headers)
        assert res.status_code == 400
        assert "not connected" in res.json()["detail"]

    def test_missing_itinerary_returns_400(self):
        headers, user_id = get_auth_header("user_no_itinerary@example.com")
        connect_user_google_calendar(user_id)
        trip_id = setup_test_trip(user_id, with_itinerary=False)

        res = client.post(f"/api/v1/trips/{trip_id}/calendar", headers=headers)
        assert res.status_code == 400
        assert "no generated itinerary" in res.json()["detail"]

    def test_successful_trip_scheduling(self):
        headers, user_id = get_auth_header("user_schedule_ok@example.com")
        connect_user_google_calendar(user_id)
        trip_id = setup_test_trip(user_id)

        mock_httpx_resp = MagicMock()
        mock_httpx_resp.status_code = 201
        mock_httpx_resp.json.return_value = {"id": "created_event_id"}

        with patch("httpx.post", return_value=mock_httpx_resp) as mock_post:
            res = client.post(f"/api/v1/trips/{trip_id}/calendar", headers=headers)
            assert res.status_code == 200
            data = res.json()

            assert data["total_activities"] == 4
            assert data["created"] == 4
            assert data["already_exists"] == 0
            assert data["failed"] == 0
            assert "calendar.google.com" in data["calendar_url"]
            assert mock_post.call_count == 4

            # Verify request structure sent to Google API
            call_kwargs = mock_post.call_args_list[0]
            json_body = call_kwargs.kwargs["json"]
            assert json_body["summary"] == "Arrive in Srinagar"
            assert json_body["location"] == "Dal Lake, Srinagar"
            assert "valid_access_token_abc" in call_kwargs.kwargs["headers"]["Authorization"]

    def test_idempotent_duplicate_prevention(self):
        headers, user_id = get_auth_header("user_idempotent@example.com")
        connect_user_google_calendar(user_id)
        trip_id = setup_test_trip(user_id)

        # 1st call: Google returns 201 Created
        mock_resp_create = MagicMock()
        mock_resp_create.status_code = 201

        with patch("httpx.post", return_value=mock_resp_create):
            res1 = client.post(f"/api/v1/trips/{trip_id}/calendar", headers=headers)
            assert res1.json()["created"] == 4
            assert res1.json()["already_exists"] == 0

        # 2nd call: Google returns 409 Conflict (Duplicate Event)
        mock_resp_conflict = MagicMock()
        mock_resp_conflict.status_code = 409

        with patch("httpx.post", return_value=mock_resp_conflict):
            res2 = client.post(f"/api/v1/trips/{trip_id}/calendar", headers=headers)
            assert res2.status_code == 200
            assert res2.json()["created"] == 0
            assert res2.json()["already_exists"] == 4
            assert res2.json()["failed"] == 0

    def test_partial_failure_does_not_abort_all(self):
        headers, user_id = get_auth_header("user_partial_fail@example.com")
        connect_user_google_calendar(user_id)
        trip_id = setup_test_trip(user_id)

        mock_resp_ok = MagicMock()
        mock_resp_ok.status_code = 201

        mock_resp_err = MagicMock()
        mock_resp_err.status_code = 500

        # 1st activity ok, 2nd error, 3rd ok, 4th ok
        with patch("httpx.post", side_effect=[mock_resp_ok, mock_resp_err, mock_resp_ok, mock_resp_ok]):
            res = client.post(f"/api/v1/trips/{trip_id}/calendar", headers=headers)
            assert res.status_code == 200
            data = res.json()

            assert data["total_activities"] == 4
            assert data["created"] == 3
            assert data["failed"] == 1
            assert len(data["failed_activities"]) == 1
            assert data["failed_activities"][0]["title"] == "Shikara Ride"
            assert "Google API error (500)" in data["failed_activities"][0]["error"]
