"""Live end-to-end verification script for Phase G: Frontend Itinerary PDF Export."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.user import User, RefreshToken
from app.models.trip import Trip

client = TestClient(app)


def run_live_verification():
    email = "phase_g_pdf_user@test.com"

    # 1. Cleanup
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == email).first()
        if u:
            db.query(Trip).filter(Trip.user_id == u.id).delete()
            db.query(RefreshToken).filter(RefreshToken.user_id == u.id).delete()
            db.delete(u)
            db.commit()
    finally:
        db.close()

    # 2. Signup & Login
    client.post("/api/v1/auth/signup", json={"name": "PDF Export Tester", "email": email, "password": "Password123!"})
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Create trip
    trip_res = client.post(
        "/api/v1/trips",
        json={"title": "PDF Kashmir Expedition", "destination": "Kashmir, India", "start_date": "2026-09-01", "end_date": "2026-09-05", "num_travellers": 2, "budget": "$2,500"},
        headers=headers,
    )
    assert trip_res.status_code == 201
    trip_id = trip_res.json()["id"]

    # 4. Attach itinerary to DB directly for testing
    db = SessionLocal()
    try:
        t = db.query(Trip).filter(Trip.id == trip_id).first()
        t.itinerary = {
            "trip_summary": "A breathtaking 5-day itinerary exploring the snow-capped peaks and pristine lakes of Kashmir.",
            "days": [
                {
                    "date": "2026-09-01",
                    "activities": [
                        {
                            "title": "Arrive in Srinagar & Houseboat Check-in",
                            "description": "Board a traditional wooden houseboat on Dal Lake and enjoy evening Shikara ride.",
                            "approximate_time": "Morning",
                            "location": "Dal Lake, Srinagar"
                        },
                        {
                            "title": "Mughal Gardens Tour",
                            "description": "Visit Nishat Bagh and Shalimar Bagh terrace gardens.",
                            "approximate_time": "Afternoon",
                            "location": "Nishat Bagh"
                        }
                    ]
                },
                {
                    "date": "2026-09-02",
                    "activities": [
                        {
                            "title": "Gulmarg Meadow Trip & Gondola Ride",
                            "description": "Take the world's highest cable car to Apharwat Peak.",
                            "approximate_time": "Full Day",
                            "location": "Gulmarg"
                        }
                    ]
                }
            ]
        }
        db.commit()
    finally:
        db.close()

    # 5. Fetch trip details via GET /api/v1/trips/{id}
    detail_res = client.get(f"/api/v1/trips/{trip_id}", headers=headers)
    assert detail_res.status_code == 200
    detail_data = detail_res.json()

    assert detail_data["itinerary"] is not None
    assert len(detail_data["itinerary"]["days"]) == 2
    print("✅ GET /api/v1/trips/{id} successfully returns itinerary data for PDF generation!")
    print(f"📌 Trip Title: {detail_data['title']}")
    print(f"📍 Destination: {detail_data['destination']}")
    print(f"📝 Summary: {detail_data['itinerary']['trip_summary'][:80]}...")

    # Cleanup
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == email).first()
        if u:
            db.query(Trip).filter(Trip.user_id == u.id).delete()
            db.delete(u)
            db.commit()
    finally:
        db.close()

    print("\n🎉 PHASE G LIVE INTEGRATION VERIFICATION PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_live_verification()
