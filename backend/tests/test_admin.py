"""Tests for Phase F: Admin Trip Management & Authorization Security Boundaries."""

from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User, UserRole, RefreshToken
from app.models.trip import Trip

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


def _signup_and_login(email: str, name: str = "Test User", password: str = "Password123!", role: UserRole = UserRole.USER):
    client.post("/api/v1/auth/signup", json={"name": name, "email": email, "password": password})
    
    # Set role in DB if admin requested
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user and role == UserRole.ADMIN:
            user.role = UserRole.ADMIN
            db.commit()
    finally:
        db.close()

    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()


def _auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_unauthenticated_user_cannot_access_admin_endpoints():
    """Security check 1: Unauthenticated request to /api/v1/admin/trips returns 401."""
    res_list = client.get("/api/v1/admin/trips")
    assert res_list.status_code == 401

    res_patch = client.patch("/api/v1/admin/trips/1", json={"title": "Hacked"})
    assert res_patch.status_code == 401

    res_delete = client.delete("/api/v1/admin/trips/1")
    assert res_delete.status_code == 401


def test_normal_user_cannot_access_admin_endpoints():
    """Security check 2: Normal user (UserRole.USER) receives 403 Forbidden on all /admin endpoints."""
    email = "normal_user_admin_test@test.com"
    _cleanup_user(email)
    user_tokens = _signup_and_login(email, role=UserRole.USER)
    headers = _auth_headers(user_tokens)

    # 1. GET /admin/trips
    res_list = client.get("/api/v1/admin/trips", headers=headers)
    assert res_list.status_code == 403
    assert res_list.json()["detail"] == "Insufficient permissions."

    # 2. GET /admin/trips/1
    res_get = client.get("/api/v1/admin/trips/1", headers=headers)
    assert res_get.status_code == 403

    # 3. PATCH /admin/trips/1
    res_patch = client.patch("/api/v1/admin/trips/1", json={"title": "Unauthorized Edit"}, headers=headers)
    assert res_patch.status_code == 403

    # 4. DELETE /admin/trips/1
    res_delete = client.delete("/api/v1/admin/trips/1", headers=headers)
    assert res_delete.status_code == 403

    _cleanup_user(email)


def test_admin_can_retrieve_all_trips_across_different_users():
    """Security check 3 & 4: Admin can retrieve trips belonging to User A and User B."""
    email_a = "user_a_trips@test.com"
    email_b = "user_b_trips@test.com"
    email_admin = "admin_trips_view@test.com"

    _cleanup_user(email_a)
    _cleanup_user(email_b)
    _cleanup_user(email_admin)

    tokens_a = _signup_and_login(email_a, name="User A")
    tokens_b = _signup_and_login(email_b, name="User B")
    tokens_admin = _signup_and_login(email_admin, name="Admin User", role=UserRole.ADMIN)

    # User A creates a trip
    res_a = client.post(
        "/api/v1/trips",
        json={"title": "User A Paris Trip", "destination": "Paris", "start_date": "2026-09-01", "end_date": "2026-09-05"},
        headers=_auth_headers(tokens_a),
    )
    trip_a_id = res_a.json()["id"]

    # User B creates a trip
    res_b = client.post(
        "/api/v1/trips",
        json={"title": "User B Tokyo Trip", "destination": "Tokyo", "start_date": "2026-10-01", "end_date": "2026-10-05"},
        headers=_auth_headers(tokens_b),
    )
    trip_b_id = res_b.json()["id"]

    # Admin lists ALL trips
    admin_list_res = client.get("/api/v1/admin/trips", headers=_auth_headers(tokens_admin))
    assert admin_list_res.status_code == 200
    all_trips = admin_list_res.json()

    trip_ids = [t["id"] for t in all_trips]
    assert trip_a_id in trip_ids
    assert trip_b_id in trip_ids

    # Verify user object is present in admin list item
    trip_a_admin = next(t for t in all_trips if t["id"] == trip_a_id)
    assert trip_a_admin["user"]["name"] == "User A"
    assert trip_a_admin["user"]["email"] == email_a

    # Admin GET detail of User A's trip
    admin_detail_res = client.get(f"/api/v1/admin/trips/{trip_a_id}", headers=_auth_headers(tokens_admin))
    assert admin_detail_res.status_code == 200
    assert admin_detail_res.json()["title"] == "User A Paris Trip"

    _cleanup_user(email_a)
    _cleanup_user(email_b)
    _cleanup_user(email_admin)


def test_admin_edit_modifies_metadata_only_without_touching_generated_data():
    """Security check 5, 6, 7 & 8: Admin edit modifies metadata only, without wiping or regenerating itinerary or destination_image."""
    email_user = "user_trip_owner@test.com"
    email_admin = "admin_editor@test.com"

    _cleanup_user(email_user)
    _cleanup_user(email_admin)

    tokens_user = _signup_and_login(email_user)
    tokens_admin = _signup_and_login(email_admin, role=UserRole.ADMIN)

    # 1. Create trip with existing destination_image and itinerary
    home_image = {
        "url": "https://images.pexels.com/photos/original/large.jpg",
        "photographer": "Original Photographer",
        "photographer_url": "https://pexels.com/@orig",
        "pexels_url": "https://pexels.com/photo/orig",
    }
    create_res = client.post(
        "/api/v1/trips",
        json={
            "title": "Original Title",
            "destination": "Goa, India",
            "start_date": "2026-09-01",
            "end_date": "2026-09-05",
            "destination_image": home_image,
        },
        headers=_auth_headers(tokens_user),
    )
    trip_id = create_res.json()["id"]

    # Add mock itinerary directly to DB to test non-editable preservation
    db = SessionLocal()
    try:
        t = db.query(Trip).filter(Trip.id == trip_id).first()
        t.itinerary = {"trip_summary": "Original AI Itinerary", "days": []}
        db.commit()
    finally:
        db.close()

    # 2. Admin edits destination to "London, UK" and title to "Admin Updated Title"
    with patch("app.services.trip_service.search_destination_image") as mock_pexels_spy:
        patch_res = client.patch(
            f"/api/v1/admin/trips/{trip_id}",
            json={
                "title": "Admin Updated Title",
                "destination": "London, UK",
                "status": "COMPLETED",
                "budget": "$5,000",
            },
            headers=_auth_headers(tokens_admin),
        )

        assert patch_res.status_code == 200
        data = patch_res.json()

        # Pexels MUST NOT be called for admin metadata edit
        mock_pexels_spy.assert_not_called()

        # Metadata fields updated
        assert data["title"] == "Admin Updated Title"
        assert data["destination"] == "London, UK"
        assert data["status"] == "COMPLETED"
        assert data["budget"] == "$5,000"

        # Generated fields (destination_image & itinerary) remain UNTOUCHED
        assert data["destination_image"]["url"] == "https://images.pexels.com/photos/original/large.jpg"
        assert data["itinerary"]["trip_summary"] == "Original AI Itinerary"

    _cleanup_user(email_user)
    _cleanup_user(email_admin)


def test_admin_can_delete_any_users_trip_and_normal_user_isolation_remains_intact():
    """Security check 9, 10 & 11: Admin can delete any trip. Normal user isolation remains intact."""
    email_a = "user_iso_a@test.com"
    email_b = "user_iso_b@test.com"
    email_admin = "admin_deleter@test.com"

    _cleanup_user(email_a)
    _cleanup_user(email_b)
    _cleanup_user(email_admin)

    tokens_a = _signup_and_login(email_a, name="User A")
    tokens_b = _signup_and_login(email_b, name="User B")
    tokens_admin = _signup_and_login(email_admin, role=UserRole.ADMIN)

    # User A creates trip
    trip_a = client.post(
        "/api/v1/trips",
        json={"title": "Trip A", "start_date": "2026-09-01", "end_date": "2026-09-05"},
        headers=_auth_headers(tokens_a),
    ).json()

    # User B creates trip
    trip_b = client.post(
        "/api/v1/trips",
        json={"title": "Trip B", "start_date": "2026-10-01", "end_date": "2026-10-05"},
        headers=_auth_headers(tokens_b),
    ).json()

    # 1. Normal user A lists trips -> sees ONLY Trip A
    list_a = client.get("/api/v1/trips", headers=_auth_headers(tokens_a)).json()
    assert len(list_a) == 1
    assert list_a[0]["id"] == trip_a["id"]

    # 2. Normal user A attempts to delete Trip B -> fails (404 Not Found)
    del_fail = client.delete(f"/api/v1/trips/{trip_b['id']}", headers=_auth_headers(tokens_a))
    assert del_fail.status_code == 404

    # 3. Admin deletes Trip B -> succeeds (204 No Content)
    del_admin = client.delete(f"/api/v1/admin/trips/{trip_b['id']}", headers=_auth_headers(tokens_admin))
    assert del_admin.status_code == 204

    # 4. Verify Trip B is deleted
    get_deleted = client.get(f"/api/v1/admin/trips/{trip_b['id']}", headers=_auth_headers(tokens_admin))
    assert get_deleted.status_code == 404

    # 5. User A still has Trip A
    list_a_after = client.get("/api/v1/trips", headers=_auth_headers(tokens_a)).json()
    assert len(list_a_after) == 1
    assert list_a_after[0]["id"] == trip_a["id"]

    _cleanup_user(email_a)
    _cleanup_user(email_b)
    _cleanup_user(email_admin)
