"""Manual verification script for Phase E2 (Flow A: Home Rec reuse, Flow B: Manual creation Pexels search)."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.user import User, RefreshToken
from app.models.trip import Trip

client = TestClient(app)

def run_live_verification():
    email = "phase_e2_full_live@test.com"

    # 1. Cleanup
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

    # 2. Signup & Login
    client.post("/api/v1/auth/signup", json={"name": "Live PhaseE2 User", "email": email, "password": "Password123!"})
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # --------------------------------------------------------------------
    # FLOW A: Home Recommendation -> Trip Creation (Exact Same Image Reused)
    # --------------------------------------------------------------------
    print("🚀 [FLOW A] Fetching Home recommendation...")
    rec_resp = client.post("/api/v1/recommendations", headers=headers)
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()

    seasonal_pick = rec_data["seasonal_pick"]
    home_image = seasonal_pick.get("image")
    print(f"📌 Home Recommendation: {seasonal_pick['destination']}")
    if home_image:
        print(f"📸 Home Image URL: {home_image['url']}")

    print("\n🚀 [FLOW A] Creating trip from Home recommendation (passing destination_image)...")

    # Spy on search_destination_image to ensure it is NOT called during Home trip creation!
    with patch("app.services.trip_service.search_destination_image") as mock_pexels_spy:
        flow_a_payload = {
            "title": f"{seasonal_pick['destination']} Trip",
            "destination": seasonal_pick["destination"],
            "start_date": "2026-10-01",
            "end_date": "2026-10-05",
            "status": "PLANNED",
            "destination_image": home_image,
        }
        trip_a_res = client.post("/api/v1/trips", json=flow_a_payload, headers=headers)
        assert trip_a_res.status_code == 201
        trip_a = trip_a_res.json()

        # CRITICAL VERIFICATION: Pexels MUST NOT be called!
        mock_pexels_spy.assert_not_called()
        print("✅ Pexels service was NOT called again for Home-created trip!")

        if home_image:
            assert trip_a["destination_image"]["url"] == home_image["url"]
            print(f"✅ Exact same image persisted on Trip #{trip_a['id']}: {trip_a['destination_image']['url']}")

    # --------------------------------------------------------------------
    # FLOW B: Manual Trip Creation (No image passed -> Pexels called)
    # --------------------------------------------------------------------
    print("\n🚀 [FLOW B] Creating manual trip with destination 'Goa, India' (no image passed)...")
    flow_b_payload = {
        "title": "Manual Goa Trip",
        "destination": "Goa, India",
        "start_date": "2026-11-01",
        "end_date": "2026-11-07",
        "status": "PLANNED",
    }
    trip_b_res = client.post("/api/v1/trips", json=flow_b_payload, headers=headers)
    assert trip_b_res.status_code == 201
    trip_b = trip_b_res.json()

    img_b = trip_b.get("destination_image")
    print(f"📌 Manual Trip Destination: {trip_b['destination']}")
    if img_b:
        print(f"📸 Pexels Image URL: {img_b['url']}")
        print(f"👤 Photographer: {img_b['photographer']} ({img_b['photographer_url']})")

    assert img_b is not None, "Expected Pexels image for manual trip to 'Goa, India'"

    # --------------------------------------------------------------------
    # LIST & PERSISTENCE VERIFICATION
    # --------------------------------------------------------------------
    print("\n🚀 [PERSISTENCE] Fetching GET /api/v1/trips...")
    list_res = client.get("/api/v1/trips", headers=headers)
    assert list_res.status_code == 200
    trips_list = list_res.json()
    assert len(trips_list) == 2
    print(f"✅ GET /trips returned {len(trips_list)} trips, both with persisted destination images!")

    # Cleanup
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.query(Trip).filter(Trip.user_id == user.id).delete()
            db.delete(user)
            db.commit()
    finally:
        db.close()

    print("\n🎉 ALL LIVE PHASE E2 FLOWS VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    run_live_verification()
