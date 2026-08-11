"""Tests for the Trip CRUD API endpoints."""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User, RefreshToken
from app.models.trip import Trip

client = TestClient(app)


def _cleanup_user(email: str):
    """Remove a test user and their trips by email."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.query(Trip).filter(Trip.user_id == user.id).delete()
            db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
            db.delete(user)
            db.commit()
    finally:
        db.close()


def _signup_and_login(email: str, name: str = "Test User", password: str = "TestPass123!"):
    client.post(
        "/api/v1/auth/signup",
        json={"name": name, "email": email, "password": password},
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return resp.json()


def _auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _trip_payload(**overrides):
    start = date.today()
    end = start + timedelta(days=5)
    payload = {
        "title": "Paris Getaway",
        "destination": "Paris",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "status": "DRAFT",
    }
    payload.update(overrides)
    return payload


# ── 1. Create ────────────────────────────────────────────────────


def test_create_trip_authenticated():
    email = "trip_create@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)

    resp = client.post(
        "/api/v1/trips",
        json=_trip_payload(),
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Paris Getaway"
    assert data["destination"] == "Paris"
    assert data["status"] == "DRAFT"
    assert data["user_id"] > 0

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert data["user_id"] == user.id
    finally:
        db.close()

    _cleanup_user(email)


def test_create_trip_uses_authenticated_user_not_client_user_id():
    email = "trip_owner@test.com"
    other_email = "trip_other@test.com"
    _cleanup_user(email)
    _cleanup_user(other_email)
    tokens = _signup_and_login(email)
    other_tokens = _signup_and_login(other_email)

    db = SessionLocal()
    try:
        other_user = db.query(User).filter(User.email == other_email).first()
        other_user_id = other_user.id
    finally:
        db.close()

    resp = client.post(
        "/api/v1/trips",
        json=_trip_payload(user_id=other_user_id),
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["user_id"] != other_user_id

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert data["user_id"] == user.id
    finally:
        db.close()

    _cleanup_user(email)
    _cleanup_user(other_email)


def test_create_trip_invalid_date_range_rejected():
    email = "trip_bad_dates@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)

    start = date.today()
    end = start - timedelta(days=1)
    resp = client.post(
        "/api/v1/trips",
        json=_trip_payload(start_date=start.isoformat(), end_date=end.isoformat()),
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 422

    _cleanup_user(email)


# ── 2. Unauthenticated access ────────────────────────────────────


def test_trips_unauthenticated_rejected():
    resp = client.post("/api/v1/trips", json=_trip_payload())
    assert resp.status_code == 401

    resp = client.get("/api/v1/trips")
    assert resp.status_code == 401

    resp = client.get("/api/v1/trips/1")
    assert resp.status_code == 401

    resp = client.patch("/api/v1/trips/1", json={"title": "Updated"})
    assert resp.status_code == 401

    resp = client.delete("/api/v1/trips/1")
    assert resp.status_code == 401


# ── 3. List & get own trips ──────────────────────────────────────


def test_list_own_trips():
    email = "trip_list@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)

    client.post(
        "/api/v1/trips",
        json=_trip_payload(title="Trip One"),
        headers=_auth_headers(tokens),
    )
    client.post(
        "/api/v1/trips",
        json=_trip_payload(title="Trip Two", destination="London"),
        headers=_auth_headers(tokens),
    )

    resp = client.get("/api/v1/trips", headers=_auth_headers(tokens))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    titles = {trip["title"] for trip in data}
    assert titles == {"Trip One", "Trip Two"}

    _cleanup_user(email)


def test_get_own_trip():
    email = "trip_get@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)

    create_resp = client.post(
        "/api/v1/trips",
        json=_trip_payload(),
        headers=_auth_headers(tokens),
    )
    trip_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/trips/{trip_id}", headers=_auth_headers(tokens))
    assert resp.status_code == 200
    assert resp.json()["id"] == trip_id
    assert resp.json()["title"] == "Paris Getaway"

    _cleanup_user(email)


# ── 4. Update & delete own trips ───────────────────────────────────


def test_update_own_trip():
    email = "trip_update@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)

    create_resp = client.post(
        "/api/v1/trips",
        json=_trip_payload(),
        headers=_auth_headers(tokens),
    )
    trip_id = create_resp.json()["id"]

    resp = client.patch(
        f"/api/v1/trips/{trip_id}",
        json={"title": "Updated Title", "status": "PLANNED"},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Updated Title"
    assert data["status"] == "PLANNED"

    _cleanup_user(email)


def test_update_trip_invalid_date_range_rejected():
    email = "trip_update_bad_dates@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)

    start = date.today()
    end = start + timedelta(days=5)
    create_resp = client.post(
        "/api/v1/trips",
        json=_trip_payload(start_date=start.isoformat(), end_date=end.isoformat()),
        headers=_auth_headers(tokens),
    )
    trip_id = create_resp.json()["id"]

    resp = client.patch(
        f"/api/v1/trips/{trip_id}",
        json={"start_date": (end + timedelta(days=1)).isoformat()},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 422

    _cleanup_user(email)


def test_delete_own_trip():
    email = "trip_delete@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)

    create_resp = client.post(
        "/api/v1/trips",
        json=_trip_payload(),
        headers=_auth_headers(tokens),
    )
    trip_id = create_resp.json()["id"]

    resp = client.delete(f"/api/v1/trips/{trip_id}", headers=_auth_headers(tokens))
    assert resp.status_code == 204
    assert resp.content == b""

    get_resp = client.get(f"/api/v1/trips/{trip_id}", headers=_auth_headers(tokens))
    assert get_resp.status_code == 404

    _cleanup_user(email)


# ── 5. Cross-user access denied (404) ────────────────────────────


def _create_trip_for_user(tokens: dict, title: str = "Private Trip") -> int:
    resp = client.post(
        "/api/v1/trips",
        json=_trip_payload(title=title),
        headers=_auth_headers(tokens),
    )
    return resp.json()["id"]


def test_cannot_get_another_users_trip():
    owner_email = "trip_owner_get@test.com"
    other_email = "trip_other_get@test.com"
    _cleanup_user(owner_email)
    _cleanup_user(other_email)

    owner_tokens = _signup_and_login(owner_email)
    other_tokens = _signup_and_login(other_email)
    trip_id = _create_trip_for_user(owner_tokens)

    resp = client.get(
        f"/api/v1/trips/{trip_id}",
        headers=_auth_headers(other_tokens),
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Trip not found."

    _cleanup_user(owner_email)
    _cleanup_user(other_email)


def test_list_returns_only_own_trips():
    owner_email = "trip_owner_list@test.com"
    other_email = "trip_other_list@test.com"
    _cleanup_user(owner_email)
    _cleanup_user(other_email)

    owner_tokens = _signup_and_login(owner_email)
    other_tokens = _signup_and_login(other_email)

    _create_trip_for_user(owner_tokens, title="Owner Trip")
    _create_trip_for_user(other_tokens, title="Other Trip")

    resp = client.get("/api/v1/trips", headers=_auth_headers(owner_tokens))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Owner Trip"

    _cleanup_user(owner_email)
    _cleanup_user(other_email)


def test_cannot_update_another_users_trip():
    owner_email = "trip_owner_patch@test.com"
    other_email = "trip_other_patch@test.com"
    _cleanup_user(owner_email)
    _cleanup_user(other_email)

    owner_tokens = _signup_and_login(owner_email)
    other_tokens = _signup_and_login(other_email)
    trip_id = _create_trip_for_user(owner_tokens)

    resp = client.patch(
        f"/api/v1/trips/{trip_id}",
        json={"title": "Hacked"},
        headers=_auth_headers(other_tokens),
    )
    assert resp.status_code == 404

    owner_resp = client.get(
        f"/api/v1/trips/{trip_id}",
        headers=_auth_headers(owner_tokens),
    )
    assert owner_resp.json()["title"] == "Private Trip"

    _cleanup_user(owner_email)
    _cleanup_user(other_email)


def test_cannot_delete_another_users_trip():
    owner_email = "trip_owner_del@test.com"
    other_email = "trip_other_del@test.com"
    _cleanup_user(owner_email)
    _cleanup_user(other_email)

    owner_tokens = _signup_and_login(owner_email)
    other_tokens = _signup_and_login(other_email)
    trip_id = _create_trip_for_user(owner_tokens)

    resp = client.delete(
        f"/api/v1/trips/{trip_id}",
        headers=_auth_headers(other_tokens),
    )
    assert resp.status_code == 404

    owner_resp = client.get(
        f"/api/v1/trips/{trip_id}",
        headers=_auth_headers(owner_tokens),
    )
    assert owner_resp.status_code == 200

    _cleanup_user(owner_email)
    _cleanup_user(other_email)


def test_list_trips_filtering_and_sorting():
    email = "trip_filter_sort@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)

    today = date.today()
    # Past trip 1: ended 5 days ago
    client.post(
        "/api/v1/trips",
        json=_trip_payload(
            title="Past Trip 1",
            start_date=(today - timedelta(days=10)).isoformat(),
            end_date=(today - timedelta(days=5)).isoformat(),
        ),
        headers=_auth_headers(tokens),
    )

    # Past trip 2: ended 2 days ago (more recent start/end than Past Trip 1)
    client.post(
        "/api/v1/trips",
        json=_trip_payload(
            title="Past Trip 2",
            start_date=(today - timedelta(days=4)).isoformat(),
            end_date=(today - timedelta(days=2)).isoformat(),
        ),
        headers=_auth_headers(tokens),
    )

    # Upcoming trip 1: starts in 5 days
    client.post(
        "/api/v1/trips",
        json=_trip_payload(
            title="Upcoming Trip 1",
            start_date=(today + timedelta(days=5)).isoformat(),
            end_date=(today + timedelta(days=10)).isoformat(),
        ),
        headers=_auth_headers(tokens),
    )

    # Upcoming trip 2: starts in 2 days (closer to today)
    client.post(
        "/api/v1/trips",
        json=_trip_payload(
            title="Upcoming Trip 2",
            start_date=(today + timedelta(days=2)).isoformat(),
            end_date=(today + timedelta(days=6)).isoformat(),
        ),
        headers=_auth_headers(tokens),
    )

    # Test upcoming filtering (should return Upcoming Trip 2 first, then Upcoming Trip 1)
    resp = client.get("/api/v1/trips?status=upcoming", headers=_auth_headers(tokens))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["title"] == "Upcoming Trip 2"
    assert data[1]["title"] == "Upcoming Trip 1"

    # Test past filtering (should return Past Trip 2 first, then Past Trip 1)
    resp = client.get("/api/v1/trips?status=past", headers=_auth_headers(tokens))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["title"] == "Past Trip 2"
    assert data[1]["title"] == "Past Trip 1"

    # Test all filtering (default / status=all)
    resp = client.get("/api/v1/trips?status=all", headers=_auth_headers(tokens))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 4

    _cleanup_user(email)
