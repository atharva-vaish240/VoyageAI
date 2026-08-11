"""Tests for Phase E2: My Trips destination images & Pexels integration."""

from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User, RefreshToken
from app.models.trip import Trip
from app.schemas.recommendation import RecommendationImage

client = TestClient(app)


def _cleanup_user(email: str):
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


def _signup_and_login(email: str, name: str = "Trip Image User", password: str = "Password123!"):
    client.post("/api/v1/auth/signup", json={"name": name, "email": email, "password": password})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()


def _auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_home_created_trip_persists_existing_image_without_calling_pexels():
    """Case 1: Home-created trip with existing destination_image persists directly and DOES NOT call Pexels again."""
    email = "home_trip_img@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)

    home_image = {
        "url": "https://images.pexels.com/photos/home123/large.jpg",
        "photographer": "Home Photographer",
        "photographer_url": "https://www.pexels.com/@homephoto",
        "pexels_url": "https://www.pexels.com/photo/home123",
    }

    with patch("app.services.trip_service.search_destination_image") as mock_pexels:
        payload = {
            "title": "Kashmir Valley Trip",
            "destination": "Kashmir, India",
            "start_date": "2026-09-01",
            "end_date": "2026-09-07",
            "status": "PLANNED",
            "destination_image": home_image,
        }
        res = client.post("/api/v1/trips", json=payload, headers=_auth_headers(tokens))

        assert res.status_code == 201
        data = res.json()

        # Pexels MUST NOT be called because destination_image was already supplied
        mock_pexels.assert_not_called()

        # Image persisted
        assert data["destination_image"]["url"] == "https://images.pexels.com/photos/home123/large.jpg"
        assert data["destination_image"]["photographer"] == "Home Photographer"

    _cleanup_user(email)


def test_manual_trip_calls_pexels_and_persists_image():
    """Case 2: Manual trip creation without destination_image calls Pexels service directly."""
    email = "manual_trip_img@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)

    mock_image = RecommendationImage(
        url="https://images.pexels.com/photos/manual999/large.jpg",
        photographer="Manual Photographer",
        photographer_url="https://www.pexels.com/@manual",
        pexels_url="https://www.pexels.com/photo/manual999",
    )

    with patch("app.services.trip_service.search_destination_image", return_value=mock_image) as mock_pexels:
        payload = {
            "title": "Goa Beach Vacation",
            "destination": "Goa, India",
            "start_date": "2026-09-01",
            "end_date": "2026-09-07",
            "status": "PLANNED",
        }
        res = client.post("/api/v1/trips", json=payload, headers=_auth_headers(tokens))

        assert res.status_code == 201
        data = res.json()

        # Verify Pexels called with destination string
        mock_pexels.assert_called_once_with("Goa, India")
        assert data["destination_image"]["url"] == "https://images.pexels.com/photos/manual999/large.jpg"

    _cleanup_user(email)


def test_pexels_failure_still_creates_trip():
    """Case 3: Pexels failure during trip creation still succeeds with destination_image = None."""
    email = "pexels_fail_trip@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)

    with patch("app.services.trip_service.search_destination_image", side_effect=Exception("Pexels timeout")):
        payload = {
            "title": "Mountain Hike",
            "destination": "Unknown Ridge",
            "start_date": "2026-10-01",
            "end_date": "2026-10-05",
        }
        res = client.post("/api/v1/trips", json=payload, headers=_auth_headers(tokens))

        assert res.status_code == 201
        data = res.json()
        assert data["destination_image"] is None
        assert data["destination"] == "Unknown Ridge"

    _cleanup_user(email)


def test_get_trips_returns_persisted_destination_image():
    """Case 4: GET /api/v1/trips and GET /api/v1/trips/{id} return persisted destination_image."""
    email = "get_trips_img@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)

    home_image = {
        "url": "https://images.pexels.com/photos/persist/large.jpg",
        "photographer": "Persist Photographer",
        "photographer_url": "https://www.pexels.com/@persist",
        "pexels_url": "https://www.pexels.com/photo/persist",
    }

    # Create trip with image
    create_res = client.post(
        "/api/v1/trips",
        json={
            "title": "Saved Trip",
            "destination": "Paris",
            "start_date": "2026-11-01",
            "end_date": "2026-11-05",
            "destination_image": home_image,
        },
        headers=_auth_headers(tokens),
    )
    trip_id = create_res.json()["id"]

    # Verify GET /trips list
    list_res = client.get("/api/v1/trips", headers=_auth_headers(tokens))
    assert list_res.status_code == 200
    trips_list = list_res.json()
    assert len(trips_list) == 1
    assert trips_list[0]["destination_image"]["url"] == "https://images.pexels.com/photos/persist/large.jpg"

    # Verify GET /trips/{id} detail
    detail_res = client.get(f"/api/v1/trips/{trip_id}", headers=_auth_headers(tokens))
    assert detail_res.status_code == 200
    assert detail_res.json()["destination_image"]["photographer"] == "Persist Photographer"

    _cleanup_user(email)


def test_patch_trip_destination_refetches_pexels_image():
    """Test PATCH /api/v1/trips/{id} refetches Pexels photo when destination changes, but not when destination is unchanged."""
    email = "trip_patch_img@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)

    img_old = RecommendationImage(
        url="https://images.pexels.com/old.jpg",
        photographer="Old Photographer",
        photographer_url="https://pexels.com/old",
        pexels_url="https://pexels.com/photo/old",
    )
    img_new = RecommendationImage(
        url="https://images.pexels.com/new.jpg",
        photographer="New Photographer",
        photographer_url="https://pexels.com/new",
        pexels_url="https://pexels.com/photo/new",
    )

    with patch("app.services.trip_service.search_destination_image", return_value=img_old):
        create_res = client.post(
            "/api/v1/trips",
            json={"title": "Original Trip", "destination": "Paris", "start_date": "2026-09-01", "end_date": "2026-09-05"},
            headers=_auth_headers(tokens),
        )
        trip_id = create_res.json()["id"]

    # Update title ONLY -> destination unchanged -> Pexels should NOT be called
    with patch("app.services.trip_service.search_destination_image") as mock_pexels_unused:
        patch_res = client.patch(
            f"/api/v1/trips/{trip_id}",
            json={"title": "Updated Title Only"},
            headers=_auth_headers(tokens),
        )
        assert patch_res.status_code == 200
        mock_pexels_unused.assert_not_called()
        assert patch_res.json()["destination_image"]["url"] == "https://images.pexels.com/old.jpg"

    # Update destination -> destination changed -> Pexels SHOULD be called with new destination
    with patch("app.services.trip_service.search_destination_image", return_value=img_new) as mock_pexels_new:
        patch_res2 = client.patch(
            f"/api/v1/trips/{trip_id}",
            json={"destination": "Tokyo, Japan"},
            headers=_auth_headers(tokens),
        )
        assert patch_res2.status_code == 200
        mock_pexels_new.assert_called_once_with("Tokyo, Japan")
        assert patch_res2.json()["destination_image"]["url"] == "https://images.pexels.com/new.jpg"

    _cleanup_user(email)
