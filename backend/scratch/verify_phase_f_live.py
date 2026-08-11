"""Live end-to-end verification script for Phase F: Admin Trip Management & Authorization."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.user import User, UserRole, RefreshToken
from app.models.trip import Trip

client = TestClient(app)


def run_live_verification():
    email_a = "phase_f_user_a@test.com"
    email_b = "phase_f_user_b@test.com"
    email_admin = "phase_f_admin@test.com"

    # 1. Cleanup old users
    db = SessionLocal()
    try:
        for em in [email_a, email_b, email_admin]:
            u = db.query(User).filter(User.email == em).first()
            if u:
                db.query(Trip).filter(Trip.user_id == u.id).delete()
                db.query(RefreshToken).filter(RefreshToken.user_id == u.id).delete()
                db.delete(u)
        db.commit()
    finally:
        db.close()

    print("🔑 Creating Users (User A, User B, Admin)...")
    client.post("/api/v1/auth/signup", json={"name": "User A", "email": email_a, "password": "Password123!"})
    client.post("/api/v1/auth/signup", json={"name": "User B", "email": email_b, "password": "Password123!"})
    client.post("/api/v1/auth/signup", json={"name": "Admin Boss", "email": email_admin, "password": "Password123!"})

    # Elevate admin user role in DB
    db = SessionLocal()
    try:
        admin_u = db.query(User).filter(User.email == email_admin).first()
        admin_u.role = UserRole.ADMIN
        db.commit()
    finally:
        db.close()

    # Login all 3 users
    tokens_a = client.post("/api/v1/auth/login", json={"email": email_a, "password": "Password123!"}).json()
    tokens_b = client.post("/api/v1/auth/login", json={"email": email_b, "password": "Password123!"}).json()
    tokens_admin = client.post("/api/v1/auth/login", json={"email": email_admin, "password": "Password123!"}).json()

    headers_a = {"Authorization": f"Bearer {tokens_a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {tokens_b['access_token']}"}
    headers_admin = {"Authorization": f"Bearer {tokens_admin['access_token']}"}

    # --------------------------------------------------------------------
    # FLOW A — Normal User Isolation & Admin Access Restriction
    # --------------------------------------------------------------------
    print("\n🚀 [FLOW A] User A creates Trip A...")
    trip_a_res = client.post(
        "/api/v1/trips",
        json={"title": "User A Alps Hike", "destination": "Swiss Alps", "start_date": "2026-09-01", "end_date": "2026-09-05"},
        headers=headers_a,
    )
    assert trip_a_res.status_code == 201
    trip_a = trip_a_res.json()
    print(f"✅ Trip A created with ID #{trip_a['id']}")

    print("🔒 [FLOW A] Testing normal User A access to /api/v1/admin/trips...")
    admin_access_attempt = client.get("/api/v1/admin/trips", headers=headers_a)
    assert admin_access_attempt.status_code == 403
    print("✅ User A correctly blocked from admin endpoint (403 Forbidden)!")

    # --------------------------------------------------------------------
    # FLOW B — Admin Management (Multi-User View, Edit Metadata, Delete)
    # --------------------------------------------------------------------
    print("\n🚀 [FLOW B] User B creates Trip B...")
    trip_b_res = client.post(
        "/api/v1/trips",
        json={"title": "User B Kyoto Tour", "destination": "Kyoto, Japan", "start_date": "2026-10-01", "end_date": "2026-10-07"},
        headers=headers_b,
    )
    assert trip_b_res.status_code == 201
    trip_b = trip_b_res.json()
    print(f"✅ Trip B created with ID #{trip_b['id']}")

    print("\n👑 [FLOW B] Admin fetching ALL trips across all users (GET /api/v1/admin/trips)...")
    all_trips_res = client.get("/api/v1/admin/trips", headers=headers_admin)
    assert all_trips_res.status_code == 200
    all_trips = all_trips_res.json()
    print(f"✅ Admin sees {len(all_trips)} total trips across User A and User B!")

    admin_trip_ids = [t["id"] for t in all_trips]
    assert trip_a['id'] in admin_trip_ids
    assert trip_b['id'] in admin_trip_ids

    print("\n✏️ [FLOW B] Admin updating metadata for User A's Trip A (PATCH /api/v1/admin/trips/{id})...")
    with patch("app.services.trip_service.search_destination_image") as mock_pexels_spy:
        patch_res = client.patch(
            f"/api/v1/admin/trips/{trip_a['id']}",
            json={"title": "Admin Updated Alps Hike", "destination": "Valais, Switzerland", "budget": "$4,000"},
            headers=headers_admin,
        )
        assert patch_res.status_code == 200
        patched_a = patch_res.json()

        mock_pexels_spy.assert_not_called()
        print("✅ Pexels was NOT called during admin edit!")
        print(f"✅ Trip A metadata updated: title='{patched_a['title']}', destination='{patched_a['destination']}'")

    print("\n🗑️ [FLOW B] Admin deleting User B's Trip B (DELETE /api/v1/admin/trips/{id})...")
    del_res = client.delete(f"/api/v1/admin/trips/{trip_b['id']}", headers=headers_admin)
    assert del_res.status_code == 204
    print("✅ Trip B deleted successfully by Admin!")

    # Verify Trip B is no longer in admin list
    all_trips_after = client.get("/api/v1/admin/trips", headers=headers_admin).json()
    assert trip_b['id'] not in [t["id"] for t in all_trips_after]
    print("✅ Trip B no longer present in admin trip list!")

    # --------------------------------------------------------------------
    # FLOW C — Normal User Regression Check
    # --------------------------------------------------------------------
    print("\n🚀 [FLOW C] Verifying User A isolation remains intact...")
    list_a_after = client.get("/api/v1/trips", headers=headers_a).json()
    assert len(list_a_after) == 1
    assert list_a_after[0]["id"] == trip_a['id']
    assert list_a_after[0]["title"] == "Admin Updated Alps Hike"
    print("✅ User A sees ONLY their own updated trip. Isolation 100% intact!")

    # Cleanup
    db = SessionLocal()
    try:
        for em in [email_a, email_b, email_admin]:
            u = db.query(User).filter(User.email == em).first()
            if u:
                db.query(Trip).filter(Trip.user_id == u.id).delete()
                db.delete(u)
        db.commit()
    finally:
        db.close()

    print("\n🎉 ALL PHASE F ADMIN FLOWS & SECURITY BOUNDARIES VERIFIED SUCCESSFULLY!")


if __name__ == "__main__":
    run_live_verification()
